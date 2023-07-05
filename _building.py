import streamlit as st
import folium
import re
import pandas as pd
import numpy as np
import unicodedata
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy import create_engine
from bs4 import BeautifulSoup
from streamlit_folium import st_folium


from scripts.datafunctions import inputvar_complemento,forecast,getinfobarrio,getvalorizacion,getcaracterizacion,getcomparables
from scripts.html_scripts import table2,table3,boxkpi,boxnumbermoney

user     = st.secrets["user_appraisal"]
password = st.secrets["password_appraisal"]
host     = st.secrets["host_appraisal"]
schema   = st.secrets["schema_appraisal"]


def remover_tildes(input_str):
    nfkd_form  = unicodedata.normalize('NFD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii.decode()

def str2num(x):
    try: return int(float(x))
    except: return x
    
@st.experimental_memo
def getdatabuilding(comuna,direccion):
    
    try: direccion = remover_tildes(direccion)
    except: pass
    
    consulta = f'WHERE zona3="{comuna}"'
    
    dirstr   = re.sub('[^a-zA-Z]',' ',direccion).strip()
    dirstr   = re.sub(' +', ' ', dirstr)
    if dirstr!='':
        consulta += ' AND direccion LIKE "%' + '%" AND direccion LIKE "%'.join(dirstr.split(' '))+'%"'
    
    dirnum   = re.sub('[^0-9]',' ',direccion).strip()
    dirnum   = re.sub(' +', ' ', dirnum)
    if dirstr!='':
        consulta += ' AND direccion LIKE "%' + '%" AND direccion LIKE "%'.join(dirnum.split(' '))+'%"'
        
    engine       = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    dataventa    = pd.read_sql_query(f"""SELECT code,zona3, zona4,direccion,descripcion,url,fecha_inicial,rango,areaconstruida,valorventa,valorarriendo,valormt2,habitaciones,banos,garajes,img1 FROM appraisal.chile_venta_apartamento_market {consulta}""" , engine)
    dataarriendo = pd.read_sql_query(f"""SELECT code,zona3, zona4,direccion,descripcion,url,fecha_inicial,rango,areaconstruida,valorventa,valorarriendo,valormt2,habitaciones,banos,garajes,img1 FROM appraisal.chile_arriendo_apartamento_market {consulta}""" , engine)
    engine.dispose()
    return dataventa,dataarriendo

@st.experimental_memo
def getalldata(codigo):
    engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    tablaventa         = 'chile_venta_apartamento_barrio'
    tablaarriendo      = 'chile_arriendo_apartamento_barrio'
    databarrioventa    = pd.read_sql_query(f"""SELECT * FROM appraisal.{tablaventa} WHERE codigo='{codigo}'"""  , engine)
    databarrioarriendo = pd.read_sql_query(f"""SELECT * FROM appraisal.{tablaarriendo} WHERE codigo='{codigo}'""" , engine)
    
    databarrio = pd.DataFrame()
    if databarrioventa.empty is False:
        databarrioventa['tiponegocio'] = 'Venta'
        databarrio = pd.concat([databarrio,databarrioventa])
    if databarrioarriendo.empty is False:
        databarrioarriendo['tiponegocio'] = 'Arriendo'
        databarrio = pd.concat([databarrio,databarrioarriendo])
    
    if databarrio.empty is False:
        databarrio['combinacion'] = None
        idd = databarrio['tipo']=='barrio'
        if sum(idd)>0:
            databarrio.loc[idd,'combinacion'] = ''
            
        idd = databarrio['tipo']=='complemento'
        if sum(idd)>0:
            databarrio.loc[idd,'combinacion'] = databarrio.loc[idd,'habitaciones'].astype(int).astype(str)+' D + '+databarrio.loc[idd,'banos'].astype(int).astype(str)+' B'

        idd = databarrio['tipo']=='complemento_garaje'
        if sum(idd)>0:
            databarrio.loc[idd,'combinacion'] = databarrio.loc[idd,'habitaciones'].astype(int).astype(str)+' D + '+databarrio.loc[idd,'banos'].astype(int).astype(str)+' B + '+databarrio.loc[idd,'garajes'].astype(int).astype(str)+' E'
        
    tablaventa               = 'chile_venta_apartamento_valorizacion'
    tablaarriendo            = 'chile_arriendo_apartamento_valorizacion'
    datavalorizacionventa    = pd.read_sql_query(f"""SELECT * FROM appraisal.{tablaventa} WHERE codigo='{codigo}'"""  , engine)
    datavalorizacionarriendo = pd.read_sql_query(f"""SELECT * FROM appraisal.{tablaarriendo} WHERE codigo='{codigo}'""" , engine)

    datavalorizacion = pd.DataFrame()
    if datavalorizacionventa.empty is False:
        datavalorizacionventa['tiponegocio'] = 'Venta'
        datavalorizacion = pd.concat([datavalorizacion,datavalorizacionventa])
    if datavalorizacionarriendo.empty is False:
        datavalorizacionarriendo['tiponegocio'] = 'Arriendo'
        datavalorizacion = pd.concat([datavalorizacion,datavalorizacionarriendo])
        
    if datavalorizacion.empty is False:
        datavalorizacion['combinacion'] = None
        idd = datavalorizacion['tipo']=='barrio'
        if sum(idd)>0:
            datavalorizacion.loc[idd,'combinacion'] = ''
            
        idd = datavalorizacion['tipo']=='complemento'
        if sum(idd)>0:
            datavalorizacion.loc[idd,'combinacion'] = datavalorizacion.loc[idd,'habitaciones'].astype(int).astype(str)+' D + '+datavalorizacion.loc[idd,'banos'].astype(int).astype(str)+' B'

        idd = datavalorizacion['tipo']=='complemento_garaje'
        if sum(idd)>0:
            datavalorizacion.loc[idd,'combinacion'] = datavalorizacion.loc[idd,'habitaciones'].astype(int).astype(str)+' D + '+datavalorizacion.loc[idd,'banos'].astype(int).astype(str)+' B + '+datavalorizacion.loc[idd,'garajes'].astype(int).astype(str)+' E'
        
        
    tablaventa                  = 'chile_venta_apartamento_caracterizacion'
    tablaarriendo               = 'chile_arriendo_apartamento_caracterizacion'
    datacaracterizacionventa    = pd.read_sql_query(f"""SELECT variable,valor,tipo FROM appraisal.{tablaventa} WHERE codigo='{codigo}'"""  , engine)
    datacaracterizacionarriendo = pd.read_sql_query(f"""SELECT variable,valor,tipo FROM appraisal.{tablaarriendo} WHERE codigo='{codigo}'""" , engine)
    
    datacaracterizacion = pd.DataFrame()
    if datacaracterizacionventa.empty is False:
        datacaracterizacionventa['tiponegocio'] = 'Venta'
        datacaracterizacion = pd.concat([datacaracterizacion,datacaracterizacionventa])
    if datacaracterizacionarriendo.empty is False:
        datacaracterizacionarriendo['tiponegocio'] = 'Arriendo'
        datacaracterizacion = pd.concat([datacaracterizacion,datacaracterizacionarriendo])
        
    engine.dispose()
    
    #return databarrioventa,databarrioarriendo,datavalorizacionventa,datavalorizacionarriendo,datacaracterizacionventa,datacaracterizacionarriendo
    return databarrio,datavalorizacion,datacaracterizacion

def main():
    formato = {
        'inputvar':{},
        'access_building':False,
              }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
        
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.selectbox('Ciudad',options=['Santiago'])
    with col2:
        direccion = st.text_input('Dirección',value='')
    with col3:
        comuna = st.selectbox('Comuna', options=['','Cerrillos', 'Cerro Navia', 'Conchalí', 'El Bosque', 'Estación Central', 'Huechuraba', 'Independencia', 'La Cisterna', 'La Florida', 'La Granja', 'La Pintana', 'La Reina', 'Las Condes', 'Lo Barnechea', 'Lo Espejo', 'Lo Prado', 'Macul', 'Maipú', 'Ñuñoa', 'Pedro Aguirre Cerda', 'Peñalolén', 'Providencia', 'Pudahuel', 'Quilicura', 'Quinta Normal', 'Recoleta', 'Renca', 'San Joaquín', 'San Miguel', 'San Ramón', 'Santiago', 'Vitacura'])
    with col4:
        st.write('')
        st.write('')
    with col4:
        summit = st.button('Buscar')
        if summit:
            st.session_state.access_building = True
    
    if st.session_state.access_building:
        st.write('---')
        direccionformato = f'{direccion},{comuna},chile'
        st.session_state.inputvar = {
                     'direccion': direccionformato
                     }
    
        st.session_state.inputvar = inputvar_complemento(st.session_state.inputvar)
        st.session_state.inputvar['direccion'] = direccion
        
        codigo = st.session_state.inputvar['codigo']
        
        #-------------------------------------------------------------------------#
        # DESCRIPCION Y MAPA
        #-------------------------------------------------------------------------#
        col1, col2 = st.columns(2)
    
        formato = [{'name':'Comuna','value':'zona3'},
                   {'name':'Barrio','value':'zona4'},
                   {'name':'Dirección','value':'direccion'},
                   ]
        
        html = ""
        for i in formato:
            htmlpaso = ""
            if i['value'] in st.session_state.inputvar:
                htmlpaso += f"""
                <td>{i["name"]}</td>
                <td>{st.session_state.inputvar[i['value']]}</td>            
                """
                html += f"""
                    <tr>
                    {htmlpaso}
                    </tr>
                """
        texto = BeautifulSoup(table2(html,'Descripción'), 'html.parser')
        with col1:
            st.markdown(texto, unsafe_allow_html=True)          
        
        if 'latitud' in st.session_state.inputvar and 'longitud' in st.session_state.inputvar:
            with col2:
                m      = folium.Map(location=[st.session_state.inputvar['latitud'], st.session_state.inputvar['longitud']], zoom_start=16,tiles="cartodbpositron")
                folium.Marker(location=[st.session_state.inputvar['latitud'], st.session_state.inputvar['longitud']]).add_to(m)
                st_map = st_folium(m,width=800,height=450)
                    
        if 'zona3' in st.session_state.inputvar:
            comuna = st.session_state.inputvar['zona3']
        dataventa,datarriendo = getdatabuilding(comuna,direccion)
    
        #-------------------------------------------------------------------------#
        # OFERTA - VENTA
        #-------------------------------------------------------------------------#
        if dataventa.empty is False:
            idd  = dataventa['img1'].isnull()
            if sum(idd)>0:
                dataventa[idd,'img1'] = "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
    
            st.markdown('<div style="background-color: #f2f2f2; border: 1px solid #fff; padding: 0px; margin-bottom: 20px;"><h1 style="margin: 0; font-size: 18px; text-align: center; color: #3A5AFF;">Inmuebles en oferta para <b>venta</b></h1></div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1,1,4])
            with col1: 
                label       = '<label>Total ofertas<br>(último año)</label>'
                html        = boxkpi(len(dataventa),label)
                html_struct = BeautifulSoup(html, 'html.parser')
                st.markdown(html_struct, unsafe_allow_html=True)        
            
            with col2: 
                label       = '<label>Valor venta promedio<br>(mt2, UF)</label>'
                html        = boxkpi(f'${dataventa["valormt2"].median():,.0f}',label)
                html_struct = BeautifulSoup(html, 'html.parser')
                st.markdown(html_struct, unsafe_allow_html=True)    
            
            with col3:
                grupoofertasventa = dataventa.groupby(['rango','habitaciones','banos','garajes'],dropna=False)['valormt2'].median().reset_index()
                grupoofertasventa = grupoofertasventa[grupoofertasventa['valormt2'].notnull()]
                grupoofertasventa.index = range(len(grupoofertasventa))
                grupoofertasventa = grupoofertasventa.sort_values(by=['rango','habitaciones','banos','garajes'],ascending=True)
                grupoofertasventa['valormt2'] = grupoofertasventa['valormt2'].apply(lambda x: f'${x:,.0f}')
                idd = grupoofertasventa['garajes'].isnull()
                if sum(idd)>0:
                    grupoofertasventa.loc[idd,'garajes'] = ''
                grupoofertasventa.rename(columns={'rango':'Rango de area','habitaciones':'# Dormitorios','banos':'# Baños','garajes':'# Estacionamientos','valormt2':'Valor por mt2'},inplace=True)
                
                st.dataframe(grupoofertasventa)
    
            
            imagenes = ''
            for i, inmueble in dataventa.iterrows():
                if isinstance(inmueble['img1'], str) and len(inmueble['img1'])>20: imagen_principal =  inmueble['img1']
                else: imagen_principal = "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
                
                try:    garajes_inmueble = f' | <strong>{int(inmueble["garajes"])}</strong> pq'
                except: garajes_inmueble = ""
                    
                propertyinfo = f'<strong>{inmueble["areaconstruida"]}</strong> mt<sup>2</sup> | <strong>{int(inmueble["habitaciones"])}</strong> hab | <strong>{int(inmueble["banos"])}</strong> baños {garajes_inmueble}'
                url_export   = f"https://buydepa-app-chile.streamlit.app/Ficha?code={inmueble['code']}&tiponegocio=Venta&tipoinmueble=Apartamento" 
    
                if isinstance(inmueble['direccion'], str): direccion = inmueble['direccion'][0:35]
                else: direccion = '&nbsp'
                imagenes += f'''    
                  <div class="propiedad">
                    <a href="{url_export}" target="_blank">
                    <div class="imagen">
                      <img src="{imagen_principal}">
                    </div>
                    </a>
                    <div class="caracteristicas">
                      <h3>${inmueble['valorventa']:,.0f}</h3>
                      <p>{direccion}</p>
                      <p>{propertyinfo}</p>
                    </div>
                  </div>
                  '''
                
            style = """
                <style>
                  .contenedor-propiedades {
                    overflow-x: scroll;
                    white-space: nowrap;
                    margin-bottom: 40px;
                    margin-top: 30px;
                  }
                  
                  .propiedad {
                    display: inline-block;
                    vertical-align: top;
                    margin-right: 20px;
                    text-align: center;
                    width: 300px;
                  }
                  
                  .imagen {
                    height: 200px;
                    margin-bottom: 10px;
                    overflow: hidden;
                  }
                  
                  .imagen img {
                    display: block;
                    height: 100%;
                    width: 100%;
                    object-fit: cover;
                  }
                  
                  .caracteristicas {
                    background-color: #f2f2f2;
                    padding: 4px;
                    text-align: left;
                  }
                  
                  .caracteristicas h3 {
                    font-size: 18px;
                    margin-top: 0;
                  }
                  .caracteristicas p {
                    font-size: 14px;
                    margin-top: 0;
                  }
                  .caracteristicas p1 {
                    font-size: 12px;
                    text-align: left;
                    width:40%;
                    padding: 8px;
                    background-color: #294c67;
                    color: #ffffff;
                    margin-top: 0;
                  }
                  .caracteristicas p2 {
                    font-size: 12px;
                    text-align: left;
                    width:40%;
                    padding: 8px;
                    background-color: #008f39;
                    color: #ffffff;
                    margin-top: 0;
                  } 
                </style>
            """
            
            html = f"""
            <!DOCTYPE html>
            <html>
              <head>
                <meta charset="UTF-8">
                {style}
              </head>
              <body>
                <div class="contenedor-propiedades">
                {imagenes}
                </div>
              </body>
            </html>
            """
            texto = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
    
            #-------------------------------------------------------------------------#
            # OFERTA - ARRIENDO
            #-------------------------------------------------------------------------#
            if datarriendo.empty is False:
                idd  = datarriendo['img1'].isnull()
                if sum(idd)>0:
                    datarriendo[idd,'img1'] = "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
    
                st.markdown('<div style="background-color: #f2f2f2; border: 1px solid #fff; padding: 0px; margin-bottom: 20px;"><h1 style="margin: 0; font-size: 18px; text-align: center; color: #3A5AFF;">Inmuebles en oferta para <b>arriendo</b></h1></div>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([1,1,4])
                with col1: 
                    label       = '<label>Total ofertas<br>(último año)</label>'
                    html        = boxkpi(len(datarriendo),label)
                    html_struct = BeautifulSoup(html, 'html.parser')
                    st.markdown(html_struct, unsafe_allow_html=True)        
                
                with col2: 
                    label       = '<label>Valor venta promedio<br>(mt2, UF)</label>'
                    html        = boxkpi(f'${datarriendo["valormt2"].median():,.2f}',label)
                    html_struct = BeautifulSoup(html, 'html.parser')
                    st.markdown(html_struct, unsafe_allow_html=True)    
                
                with col3:
                    grupoofertasarriendo = datarriendo.groupby(['rango','habitaciones','banos','garajes'],dropna=False)['valormt2'].median().reset_index()
                    grupoofertasarriendo = grupoofertasarriendo[grupoofertasarriendo['valormt2'].notnull()]
                    grupoofertasarriendo.index = range(len(grupoofertasarriendo))
                    grupoofertasarriendo = grupoofertasarriendo.sort_values(by=['rango','habitaciones','banos','garajes'],ascending=True)
                    grupoofertasarriendo['valormt2'] = grupoofertasarriendo['valormt2'].apply(lambda x: f'${x:,.2f}')
                    idd = grupoofertasarriendo['garajes'].isnull()
                    if sum(idd)>0:
                        grupoofertasarriendo.loc[idd,'garajes'] = ''
                    grupoofertasarriendo.rename(columns={'rango':'Rango de area','habitaciones':'# Dormitorios','banos':'# Baños','garajes':'# Estacionamientos','valormt2':'Valor por mt2'},inplace=True)
                    st.dataframe(grupoofertasarriendo)
        
                
                imagenes = ''
                for i, inmueble in datarriendo.iterrows():
                    if isinstance(inmueble['img1'], str) and len(inmueble['img1'])>20: imagen_principal =  inmueble['img1']
                    else: imagen_principal = "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
                    
                    try:    garajes_inmueble = f' | <strong>{int(inmueble["garajes"])}</strong> pq'
                    except: garajes_inmueble = ""
                        
                    propertyinfo = f'<strong>{inmueble["areaconstruida"]}</strong> mt<sup>2</sup> | <strong>{int(inmueble["habitaciones"])}</strong> hab | <strong>{int(inmueble["banos"])}</strong> baños {garajes_inmueble}'
                    url_export   = f"https://buydepa-app-colombia.streamlit.app/Ficha?code={inmueble['code']}&tiponegocio=Arriendo&tipoinmueble=Apartamento" 
        
                    if isinstance(inmueble['direccion'], str): direccion = inmueble['direccion'][0:35]
                    else: direccion = '&nbsp'
                    imagenes += f'''    
                      <div class="propiedad">
                        <a href="{url_export}" target="_blank">
                        <div class="imagen">
                          <img src="{imagen_principal}">
                        </div>
                        </a>
                        <div class="caracteristicas">
                          <h3>${inmueble['valorarriendo']:,.0f}</h3>
                          <p>{direccion}</p>
                          <p>{propertyinfo}</p>
                        </div>
                      </div>
                      '''
                    
                style = """
                    <style>
                      .contenedor-propiedades {
                        overflow-x: scroll;
                        white-space: nowrap;
                        margin-bottom: 40px;
                        margin-top: 30px;
                      }
                      
                      .propiedad {
                        display: inline-block;
                        vertical-align: top;
                        margin-right: 20px;
                        text-align: center;
                        width: 300px;
                      }
                      
                      .imagen {
                        height: 200px;
                        margin-bottom: 10px;
                        overflow: hidden;
                      }
                      
                      .imagen img {
                        display: block;
                        height: 100%;
                        width: 100%;
                        object-fit: cover;
                      }
                      
                      .caracteristicas {
                        background-color: #f2f2f2;
                        padding: 4px;
                        text-align: left;
                      }
                      
                      .caracteristicas h3 {
                        font-size: 18px;
                        margin-top: 0;
                      }
                      .caracteristicas p {
                        font-size: 14px;
                        margin-top: 0;
                      }
                      .caracteristicas p1 {
                        font-size: 12px;
                        text-align: left;
                        width:40%;
                        padding: 8px;
                        background-color: #294c67;
                        color: #ffffff;
                        margin-top: 0;
                      }
                      .caracteristicas p2 {
                        font-size: 12px;
                        text-align: left;
                        width:40%;
                        padding: 8px;
                        background-color: #008f39;
                        color: #ffffff;
                        margin-top: 0;
                      } 
                    </style>
                """
                
                html = f"""
                <!DOCTYPE html>
                <html>
                  <head>
                    <meta charset="UTF-8">
                    {style}
                  </head>
                  <body>
                    <div class="contenedor-propiedades">
                    {imagenes}
                    </div>
                  </body>
                </html>
                """
                texto = BeautifulSoup(html, 'html.parser')
                st.markdown(texto, unsafe_allow_html=True)
               
        #-------------------------------------------------------------------------#
        # REFERENCIA DE PRECIOS BARRIO
        #-------------------------------------------------------------------------#
    
        st.markdown('<div style="background-color: #f2f2f2; border: 1px solid #fff; padding: 0px; margin-bottom: 20px;"><h1 style="margin: 0; font-size: 18px; text-align: center; color: #3A5AFF;">Referencia de precios en el barrio</h1></div>', unsafe_allow_html=True)
        databarrio,datavalorizacion,datacaracterizacion = getalldata(codigo)
        
        col1, col2 = st.columns(2)
        with col1:
            sel_tiponegocio = st.selectbox('Tipo de negocio',options=['Venta','Arriendo'])
        with col2:
            opciones = list(databarrio[databarrio['tiponegocio']==sel_tiponegocio]['combinacion'].unique())+list(datavalorizacion[datavalorizacion['tiponegocio']==sel_tiponegocio]['combinacion'].unique())
            opciones = list(set(opciones))
            opciones = sorted(opciones)
            opciones.remove('')
            opciones = ['']+opciones
            sel_tipologia = st.selectbox('Tipología',options=opciones)
        
        col    = st.columns(2)
        conteo = 0
        if databarrio.empty is False:
            idd = (databarrio['tiponegocio']==sel_tiponegocio) 
            if sel_tipologia=='':
                idd = (idd) & (databarrio['tipo']=='barrio')
            else:
                idd = (idd) & (databarrio['combinacion']==sel_tipologia)
            if sum(idd)>0:
                with col[conteo]:
                    valor = databarrio[idd]['valormt2'].iloc[0]
                    obs   = databarrio[idd]['obs'].iloc[0]
                    label = f'<label>Precio por mt <sup>2</sup><br>{sel_tiponegocio}</label>'
                    html        = boxnumbermoney(f'${valor:,.1f}' ,f'Muestra: {obs}',label)
                    html_struct = BeautifulSoup(html, 'html.parser')
                    st.markdown(html_struct, unsafe_allow_html=True) 
                    conteo += 1
                    
        if datavalorizacion.empty is False:
            idd = (datavalorizacion['tiponegocio']==sel_tiponegocio) 
            if sel_tipologia=='':
                idd = (idd) & (datavalorizacion['tipo']=='barrio')
            else:
                idd = (idd) & (datavalorizacion['combinacion']==sel_tipologia)
            if sum(idd)>0:
                with col[conteo]:
                    valor       = datavalorizacion[idd]['valorizacion'].iloc[0]
                    label       = f'<label>Valorización anual<br>{sel_tiponegocio}</label>' 
                    html        = boxnumbermoney("{:.1%}".format(valor),'&nbsp;',label)
                    html_struct = BeautifulSoup(html, 'html.parser')
                    st.markdown(html_struct, unsafe_allow_html=True) 
                    conteo += 1        
        
        #-------------------------------------------------------------------------#
        # ESTADISTICAS
        #-------------------------------------------------------------------------#
        col = st.columns(2)
        dfpaso = datacaracterizacion[datacaracterizacion['tiponegocio']==sel_tiponegocio]
        if dfpaso.empty is False:
            dfpaso['variable'] = dfpaso['variable'].apply(lambda x: str2num(x))
            formato = [{'name':'areaconstruida','label':'Área construida','order':['50 o menos mt2', '50 a 80 mt2', '80 a 100 mt2', '100 a 150 mt2','150 a 200 mt2', '200 a 300 mt2','300 o más mt2']},
                       {'name':'habitaciones','label':'Dormitorios'},
                       {'name':'banos','label':'Baños'},
                       {'name':'garajes','label':'Estacionamientos'}]
              
            conteo = 0
            for i in formato:
                df = dfpaso[dfpaso['tipo']==i['name']]
                if df.empty is False:                
                    df = df.sort_values(by='variable',ascending=True)
                    if 'order' in i:
                        df['order'] = df['variable'].replace(i['order'],range(len(i['order'])))
                        df = df.sort_values(by='order',ascending=True)
                    if conteo % 2 == 0: pos = 0
                    else: pos = 1
                    conteo += 1
                    
                    with col[pos]:
                        st.markdown(f'<div style="background-color: #f2f2f2; border: 1px solid #fff; padding: 0px; margin-bottom: 20px;"><h1 style="margin: 0; font-size: 18px; text-align: center; color: #3A5AFF;">{i["label"]}</h1></div>', unsafe_allow_html=True)            
                        fig = px.bar(df, x='variable', y='valor')
                        fig.update_traces(textposition='outside')
                        fig.update_layout(
                            plot_bgcolor='rgba(0, 0, 0, 0)',
                            paper_bgcolor='rgba(0, 0, 0, 0)',
                            xaxis_title='',
                            yaxis_title='',
                            legend_title_text=None,
                            autosize=True,
                            #xaxis={'tickangle': -90},
                            #width=800, 
                            #height=500
                        )
                        st.plotly_chart(fig, theme="streamlit",use_container_width=True) 