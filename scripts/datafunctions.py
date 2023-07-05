import streamlit as st
import re
import pandas as pd
import numpy as np
#import mysql.connector as sql
import pickle
import requests
import unicodedata
import math as mt
from urllib.parse import quote_plus
from shapely import wkt
from sqlalchemy import create_engine 

#user     = st.secrets["user"]
#password = st.secrets["password"]
#host     = st.secrets["host"]
#schema   = st.secrets["schema"]
#api_key  = st.secrets["apikey"]
#engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

user     = 'buydepa'
password = 'GWc42X887heD'
host     = 'buydepa-market.cy47rcxrw2g5.us-east-1.rds.amazonaws.com'
schema   = 'appraisal'
api_key  = 'AIzaSyAgT26vVoJnpjwmkoNaDl1Aj3NezOlSpKs'
engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

@st.experimental_memo
def getcodigo(lat,lng):
    result        = {'scacodigo':None,'codigo':None,'zona1':None,'zona2':None,'zona3':None,'zona4':None}
    data          = pd.read_sql_query(f"""SELECT scacodigo,codigo,zona1,zona2,zona3,zona4 FROM appraisal.barrios WHERE st_contains(geometry,point({lng},{lat}))""" , engine)
    #db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    #data          = pd.read_sql(f"""SELECT scacodigo,codigo,zona1,zona2,zona3,zona4 FROM appraisal.barrios WHERE st_contains(geometry,point({lng},{lat}))""" , con=db_connection)
    #db_connection.close()
    if data.empty is False:
        result = data.iloc[0].to_dict()
    return result

@st.experimental_memo
def getpolygon(lat,lng):
    result        = None
    data          = pd.read_sql_query(f"""SELECT ST_AsText(geometry) as wkt FROM appraisal.barrios WHERE st_contains(geometry,point({lng},{lat}))"""  , engine)

    #db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    #data          = pd.read_sql(f"""SELECT ST_AsText(geometry) as wkt FROM appraisal.barrios WHERE st_contains(geometry,point({lng},{lat}))""" , con=db_connection)
    #db_connection.close()
    if data.empty is False:
        result = wkt.loads(data["wkt"].iloc[0])
    return result
     
@st.experimental_memo
def getlatlng(direccion, api_key):
    resultado = {'latitud': None, 'longitud': None, 'scacodigo': None, 'codigo': None, 'zona1': None, 'zona2': None, 'zona3': None, 'zona4': None}
    direccion_codificada = quote_plus(direccion)
    url      = f"https://maps.googleapis.com/maps/api/geocode/json?address={direccion_codificada}&key={api_key}"
    response = requests.get(url)
    data     = response.json()

    if data['status'] == 'OK':
        resultado['latitud']  = data['results'][0]['geometry']['location']['lat']
        resultado['longitud'] = data['results'][0]['geometry']['location']['lng']
        resultado.update(getcodigo(resultado['latitud'],resultado['longitud']))
    return resultado
       
def inputvar_complemento(inputvar):
    direccion = inputvar['direccion']
    inputvar.update(getlatlng(direccion, api_key))
    return inputvar
    
@st.experimental_memo
def forecast(inputvar):
    
    # Colombia
    # ['areaconstruida','habitaciones','banos','garajes','estrato','codigo','tdc_codigo']
    
    # Chile
    # ['areaconstruida','habitaciones','banos','codigo']
    
    pais         = inputvar['pais']
    tipoinmueble = inputvar['tipoinmueble']
    
    # Modelo
    with open(f"data/xgboosting_{pais.lower()}_venta_{tipoinmueble.lower()}.pkl", "rb") as f:
        xgboosting_loaded_model_venta = pickle.load(f)
    
    with open(fr"data/xgboosting_{pais.lower()}_arriendo_{tipoinmueble.lower()}.pkl", "rb") as f:
        xgboosting_loaded_model_arriendo = pickle.load(f)
        
    with open('data/codigo_tiempo_de_construido.pkl', 'rb') as file:
        loaded_le_tdc = pickle.load(file)

    # Variables
    if pais.lower()=='colombia':
    
        if 'tiempoconstruido' in inputvar:
            inputvar['tdc_codigo'] = loaded_le_tdc.transform([inputvar['tiempoconstruido']])[0]
        
        inmueble = pd.DataFrame({'areaconstruida':[inputvar['areaconstruida']],
                                 'habitaciones':[int(inputvar['habitaciones'])], 
                                 'banos':[int(inputvar['banos'])], 
                                 'garajes':[int(inputvar['garajes'])],
                                 'estrato':[int(inputvar['estrato'])],
                                 'codigo':[int(inputvar['codigo'])],
                                 'tdc_codigo':[int(inputvar['tdc_codigo'])],
                                 })
        
    elif pais.lower()=='chile':
        inmueble = pd.DataFrame({'areaconstruida':[inputvar['areaconstruida']],
                                 'habitaciones':[int(inputvar['habitaciones'])], 
                                 'banos':[int(inputvar['banos'])], 
                                 'codigo':[int(inputvar['codigo'])],
                                 })
        
        if 'tiempoconstruido' in inputvar:
            inputvar['tdc_codigo'] = loaded_le_tdc.transform([inputvar['tiempoconstruido']])[0]
        #inmueble = pd.DataFrame({'areaconstruida':[inputvar['areaconstruida']],
        #                         'habitaciones':[int(inputvar['habitaciones'])], 
        #                         'banos':[int(inputvar['banos'])], 
        #                         'garajes':[int(inputvar['garajes'])], 
        #                         'codigo':[int(inputvar['codigo'])],
        #                         'tdc_codigo':[int(inputvar['tdc_codigo'])],
        #                         })        
   
    # Forecast
    log_prediccion              = xgboosting_loaded_model_venta.predict(inmueble)
    prediccion                  = np.exp(log_prediccion)
    inputvar['forecast_venta']  = prediccion[0]
    log_prediccion              = xgboosting_loaded_model_arriendo.predict(inmueble)
    prediccion                  = np.exp(log_prediccion)
    inputvar['forecast_arriendo'] = prediccion[0]
    
    # Modelo ANN
    inputvar['tiponegocio'] = 'Venta'
    r = ANNpricingforecast(inputvar)
    inputvar['forecast_venta'] = (inputvar['forecast_venta']+r['valorestimado'])/2
    
    inputvar['tiponegocio'] = 'Arriendo'
    r = ANNpricingforecast(inputvar)
    inputvar['forecast_arriendo'] = (inputvar['forecast_arriendo']+r['valorestimado'])/2
    
    return inputvar

@st.experimental_memo
def getinfobarrio(pais,tipoinmueble,codigo,areaconstruida,habitaciones=None,banos=None,garajes=None):
    tablaventa    = f'{pais.lower()}_venta_{tipoinmueble.lower()}_barrio'
    tablaarriendo = f'{pais.lower()}_arriendo_{tipoinmueble.lower()}_barrio'
    
    dataventa      = pd.read_sql_query(f"""SELECT * FROM appraisal.{tablaventa} WHERE codigo='{codigo}'"""  , engine)
    dataarriendo   = pd.read_sql_query(f"""SELECT * FROM appraisal.{tablaarriendo} WHERE codigo='{codigo}'""" , engine)

    #db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    #dataventa     = pd.read_sql(f"""SELECT * FROM appraisal.{tablaventa} WHERE codigo='{codigo}'""" , con=db_connection)
    #dataarriendo  = pd.read_sql(f"""SELECT * FROM appraisal.{tablaarriendo} WHERE codigo='{codigo}'""" , con=db_connection)
    #db_connection.close()
    
    resultado = pd.DataFrame()
    if dataventa.empty is False:
        dataventaresult = dataventa[dataventa['tipo']=='barrio']
        if habitaciones is not None and banos is not None:
            datapaso        = dataventa[(dataventa['tipo']=='complemento') & (dataventa['habitaciones']==habitaciones) & (dataventa['banos']==banos)]
            dataventaresult = pd.concat([dataventaresult,datapaso])
        if habitaciones is not None and banos is not None and garajes is not None:
            datapaso        = dataventa[(dataventa['tipo']=='complemento_garaje') & (dataventa['habitaciones']==habitaciones) & (dataventa['banos']==banos)  & (dataventa['garajes']==garajes)]
            dataventaresult = pd.concat([dataventaresult,datapaso])
        dataventaresult['tiponegocio'] = 'venta'
        resultado = pd.concat([resultado,dataventaresult])
        
    if dataarriendo.empty is False:
        dataarriendoresult = dataarriendo[dataarriendo['tipo']=='barrio']
        if habitaciones is not None and banos is not None:
            datapaso           = dataarriendo[(dataarriendo['tipo']=='complemento') & (dataarriendo['habitaciones']==habitaciones) & (dataarriendo['banos']==banos)]
            dataarriendoresult = pd.concat([dataarriendoresult,datapaso])
        if habitaciones is not None and banos is not None and garajes is not None:
            datapaso           = dataarriendo[(dataarriendo['tipo']=='complemento_garaje') & (dataarriendo['habitaciones']==habitaciones) & (dataarriendo['banos']==banos)  & (dataarriendo['garajes']==garajes)]
            dataarriendoresult = pd.concat([dataarriendoresult,datapaso])
        dataarriendoresult['tiponegocio'] = 'arriendo'
        resultado = pd.concat([resultado,dataarriendoresult])
    
    if resultado.empty is False:
        if 'valormt2' in resultado:
            resultado['valor'] = resultado['valormt2']*areaconstruida
        variables = [x for x in ['valor','obs','tipo','habitaciones','banos','garajes','tiponegocio'] if x in resultado]
        if variables!=[]: resultado = resultado[variables]
        resultado = resultado.to_dict(orient='records')
    else:
        resultado = []
    return resultado

@st.experimental_memo
def getvalorizacion(pais,tipoinmueble,codigo,habitaciones=None,banos=None,garajes=None):
    tablaventa    = f'{pais.lower()}_venta_{tipoinmueble.lower()}_valorizacion'
    tablaarriendo = f'{pais.lower()}_arriendo_{tipoinmueble.lower()}_valorizacion'
    
    dataventa      = pd.read_sql_query(f"""SELECT * FROM appraisal.{tablaventa} WHERE codigo='{codigo}'"""  , engine)
    dataarriendo   = pd.read_sql_query(f"""SELECT * FROM appraisal.{tablaarriendo} WHERE codigo='{codigo}'""" , engine)

    #db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    #dataventa     = pd.read_sql(f"""SELECT * FROM appraisal.{tablaventa} WHERE codigo='{codigo}'""" , con=db_connection)
    #dataarriendo  = pd.read_sql(f"""SELECT * FROM appraisal.{tablaarriendo} WHERE codigo='{codigo}'""" , con=db_connection)
    #db_connection.close()
    
    resultado = pd.DataFrame()
    if dataventa.empty is False:
        dataventaresult = dataventa[dataventa['tipo']=='barrio']
        if habitaciones is not None and banos is not None:
            datapaso        = dataventa[(dataventa['tipo']=='complemento') & (dataventa['habitaciones']==habitaciones) & (dataventa['banos']==banos)]
            dataventaresult = pd.concat([dataventaresult,datapaso])
        if habitaciones is not None and banos is not None and garajes is not None:
            datapaso        = dataventa[(dataventa['tipo']=='complemento_garaje') & (dataventa['habitaciones']==habitaciones) & (dataventa['banos']==banos)  & (dataventa['garajes']==garajes)]
            dataventaresult = pd.concat([dataventaresult,datapaso])
        dataventaresult['tiponegocio'] = 'venta'
        resultado = pd.concat([resultado,dataventaresult])

    if dataarriendo.empty is False:
        dataarriendoresult = dataarriendo[dataarriendo['tipo']=='barrio']
        if habitaciones is not None and banos is not None:
            datapaso           = dataarriendo[(dataarriendo['tipo']=='complemento') & (dataarriendo['habitaciones']==habitaciones) & (dataarriendo['banos']==banos)]
            dataarriendoresult = pd.concat([dataarriendoresult,datapaso])
        if habitaciones is not None and banos is not None and garajes is not None:
            datapaso           = dataarriendo[(dataarriendo['tipo']=='complemento_garaje') & (dataarriendo['habitaciones']==habitaciones) & (dataarriendo['banos']==banos)  & (dataarriendo['garajes']==garajes)]
            dataarriendoresult = pd.concat([dataarriendoresult,datapaso])
        dataarriendoresult['tiponegocio'] = 'arriendo'
        resultado = pd.concat([resultado,dataarriendoresult])
        
    if resultado.empty is False:
        variables = [x for x in ['valorizacion','tipo','habitaciones','banos','garajes','tiponegocio'] if x in resultado]
        if variables!=[]: resultado = resultado[variables]
        resultado = resultado.to_dict(orient='records')
    else:
        resultado = []
    return resultado
    
@st.experimental_memo
def getcaracterizacion(pais,tipoinmueble,codigo):
    tablaventa    = f'{pais.lower()}_venta_{tipoinmueble.lower()}_caracterizacion'
    tablaarriendo = f'{pais.lower()}_arriendo_{tipoinmueble.lower()}_caracterizacion'
    
    dataventa      = pd.read_sql_query(f"""SELECT variable,valor,tipo FROM appraisal.{tablaventa} WHERE codigo='{codigo}'"""  , engine)
    dataarriendo   = pd.read_sql_query(f"""SELECT variable,valor,tipo FROM appraisal.{tablaarriendo} WHERE codigo='{codigo}'""" , engine)

    #db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    #dataventa     = pd.read_sql(f"""SELECT variable,valor,tipo FROM appraisal.{tablaventa} WHERE codigo='{codigo}'""" , con=db_connection)
    #dataarriendo  = pd.read_sql(f"""SELECT variable,valor,tipo FROM appraisal.{tablaarriendo} WHERE codigo='{codigo}'""" , con=db_connection)
    #db_connection.close()
    
    resultado = pd.DataFrame()
    if dataventa.empty is False:
        dataventa['tiponegocio'] = 'Venta'
        resultado = pd.concat([resultado,dataventa])
    if dataarriendo.empty is False:
        dataarriendo['tiponegocio'] = 'Arriendo'
        resultado = pd.concat([resultado,dataarriendo])
        
    if resultado.empty is False:
        resultado = resultado.to_dict(orient='records')
    else:
        resultado = []        
    return resultado

@st.experimental_memo
def getcomparables(pais,tipoinmueble,codigo,zona3,areaconstruida,lat,lng,forecast_venta=None,forecast_arriendo=None,habitaciones=None,banos=None,garajes=None):
    tablaventa      = f'{pais.lower()}_venta_{tipoinmueble.lower()}_market'
    tablaarriendo   = f'{pais.lower()}_arriendo_{tipoinmueble.lower()}_market'
    metros_venta    = 150
    metros_arriendo = 150
    
    zona_filter = ''
    if 'colombia' in pais.lower():
        zona_filter = f"AND codigo = '{codigo}'"
    elif 'chile' in pais.lower():
        zona_filter = f"AND LOWER(zona3) = LOWER('{zona3}')"
        
    #db_connection = sql.connect(user=user, password=password, host=host, database=schema)
    for search_radius in  [150, 250, 500]:
        query_venta = f"""
        SELECT *, 
            ABS(habitaciones - {habitaciones}) +
            ABS(banos - {banos}) +
            {f"ABS(garajes - {garajes}) +" if garajes is not None else ""}
            ABS(valorventa - {forecast_venta if forecast_venta is not None else 0}) / {forecast_venta if forecast_venta is not None else 1} as similitud
        FROM appraisal.{tablaventa}
        WHERE habitaciones = {habitaciones} 
            AND banos = {banos}
            AND (areaconstruida BETWEEN 0.8 * {areaconstruida} AND 1.2 * {areaconstruida})
            {zona_filter}
            AND ST_Distance_Sphere(geometry, POINT({lng},{lat}))<={search_radius}
        ORDER BY similitud
        LIMIT 200
        """
        dataventa = pd.read_sql_query(query_venta , engine)
        #dataventa = pd.read_sql(query_venta, con=db_connection)
        if len(dataventa)>20:
            metros_venta = search_radius
            break
        
    for search_radius in  [150, 250, 500]:
        query_arriendo = f"""
            SELECT *,
                ABS(habitaciones - {habitaciones}) +
                ABS(banos - {banos}) +
                {f"ABS(garajes - {garajes}) +" if garajes is not None else ""}
                ABS(valorarriendo - {forecast_arriendo if forecast_arriendo is not None else 0}) / {forecast_arriendo if forecast_arriendo is not None else 1} as similitud
            FROM appraisal.{tablaarriendo}
            WHERE habitaciones = {habitaciones} 
                AND banos = {banos}
                AND (areaconstruida BETWEEN 0.8 * {areaconstruida} AND 1.2 * {areaconstruida})
                {zona_filter}
                AND ST_Distance_Sphere(geometry, POINT({lng},{lat}))<={search_radius}
            ORDER BY similitud
            LIMIT 200
        """
        dataarriendo = pd.read_sql_query(query_arriendo , engine)
        #dataarriendo  = pd.read_sql(query_arriendo, con=db_connection)
        if len(dataarriendo)>20:
            metros_arriendo = search_radius
            break
    #db_connection.close()
    
    if forecast_venta is not None and dataventa.empty is False:
        dataventa['diff_precio_venta'] = abs(dataventa['valorventa'] - forecast_venta)
        dataventa = dataventa.sort_values(by='diff_precio_venta')
    
    # Ordenar los registros seleccionados por la diferencia de precio en la tabla de arriendo
    if forecast_arriendo is not None and dataarriendo.empty is False:
        dataarriendo['diff_precio_arriendo'] = abs(dataarriendo['valorarriendo'] - forecast_arriendo)
        dataarriendo = dataarriendo.sort_values(by='diff_precio_arriendo')   
        
    return dataventa,metros_venta,dataarriendo,metros_arriendo

def similitud(row, inmueble_tipo,vardep):
    score = 0
    score += abs(row['habitaciones'] - inmueble_tipo['habitaciones'])
    score += abs(row['banos'] - inmueble_tipo['banos'])
    score += abs(row['garajes'] - inmueble_tipo['garajes'])
    score += abs(row[vardep] - inmueble_tipo[vardep]) / inmueble_tipo[vardep]
    return score


def datamodelo(filename):
    salida = pd.read_pickle(filename,compression='gzip')
    return salida

@st.experimental_memo
def ANNpricingforecast(inputvar):
    
    pais         = inputvar['pais']
    tiponegocio  = inputvar['tiponegocio']
    tipoinmueble = inputvar['tipoinmueble']
    with open(f"data/ANN_{pais.lower()}_{tiponegocio.lower()}_{tipoinmueble.lower()}.pkl", "rb") as f:
        salida = pickle.load(f)
    
    delta         = 0
    options       = salida['options']
    varlist       = salida['varlist']
    coef          = salida['coef']
    minmax        = salida['minmax']
    variables     = pd.DataFrame(0, index=np.arange(1), columns=varlist)
    
    for i in inputvar:
        value = inputvar[i]
        idd   = [z==elimina_tildes(i) for z in varlist]
        if sum(idd)==0:
            try:
                idd = [re.findall(elimina_tildes(i)+'#'+str(int(value)), z)!=[] for z in varlist]
            except:
                try:
                    idd = [re.findall(elimina_tildes(i)+'#'+elimina_tildes(value), z)!=[] for z in varlist]
                except:
                    pass
            value = 1                   
        if sum(idd)>0:
            row                = [j for j, x in enumerate(idd) if x]
            varname            = varlist[row[0]]
            variables[varname] = value
            
    # Transform MinMax
    a = variables.iloc[0]
    a = a[a!=0]
    for i in a.index:
        mini         = minmax[i]['min']
        maxi         = minmax[i]['max']
        variables[i] = (variables[i]-mini)/(maxi-mini)
        
    x     = variables.values
    value = ForecastFun(coef,x.T,options)
    if options['ytrans']=='log':
        value = np.exp(value)
        
    value         = value*(1-delta)
    valorestimado = np.round(value, int(-(mt.floor(mt.log10(value)) - 2))) 
    valuem2       = value/inputvar['areaconstruida']
    valortotal = np.round(value, int(-(mt.floor(mt.log10(value)) - 2))) 
    valuem2    = valortotal/inputvar['areaconstruida']
    return {'valorestimado': valorestimado[0][0], 'valorestimado_mt2':valuem2[0][0]}

def ForecastFun(coef,x,options):

    hiddenlayers = options['hiddenlayers']
    lambdavalue  = options['lambdavalue']
    biasunit     = options['biasunit']
    tipofun      = options['tipofun']
    numvar       = x.shape[0]
    nodos        = [numvar]
    for i in hiddenlayers:
        nodos.append(i)
    nodos.append(1)
        
    k          = len(nodos)
    suma       = 0
    theta      = [[] for i in range(k-1)]
    lambdac    = [[] for i in range(k-1)]
    lambdavect = np.nan
    for i in range(k-1):
        theta[i]   = np.reshape(coef[0:(nodos[i]+suma)*nodos[i+1]], (nodos[i]+suma, nodos[i+1]), order='F').T
        lambdac[i] =lambdavalue*np.ones(theta[i].shape)
        coef       = coef[(nodos[i]+suma)*nodos[i+1]:]
        if biasunit=='on':
            suma = 1
            lambdac[i][:,0] = 0
        [fil,col]  = lambdac[i].shape
        lambdavect = np.c_[lambdavect,np.reshape(lambdac[i],(fil*col,1)).T ]
        
    lambdac = lambdavect[:,1:].T
        
    # Forward Propagation
    a    = [[] for i in range(k)]
    z    = [[] for i in range(k)]
    g    = [[] for i in range(k)]
    a[0] = x
    numN = x.shape[1]
    for i in range(k-1):
        z[i+1]      = np.dot(theta[i],a[i])
        [ai,g[i+1]] = ANNFun(z[i+1],tipofun)
        if ((i+1)!=(k-1)) & (biasunit=='on'):
            a[i+1] = np.vstack((np.ones((1,numN)),ai))
        else:
            a[i+1] = ai
    return a[-1]

def ANNFun(z, tipofun):
    z = np.asarray(z)
    if tipofun=='lineal':
        f = z
        g = 1
    if tipofun=='logistica':
        f = 1/(1+mt.exp(-z))
        g = f*(1-f)
    if tipofun=='exp':
        f = np.exp(z)
        g = np.exp(z)
    if tipofun=='cuadratica':
        f = z + 0.5*(z*z)
        g = 1 + z
    if tipofun=='cubica':
        f = z + 0.5*(z*z)+(1/3.0)*(z*z*z)
        g = 1 + z + z*z
    return [f,g]

def elimina_tildes(s):
    s = s.replace(' ','').lower().strip()
    return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))
