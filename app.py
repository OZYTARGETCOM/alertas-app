import streamlit as st
from pymongo import MongoClient
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime
import base64

# Configuración de MongoDB Atlas
MONGO_URI = "mongodb+srv://ozytargetcom:3fbs8AbUJqW0O1F0@cluster0.k52bv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
try:
    client = MongoClient(MONGO_URI)
    db = client['alerts']
    events_collection = db['events']
except Exception as e:
    st.error(f"Error al conectar con MongoDB: {e}")
    st.stop()

# Tu clave de API de Google Maps
GOOGLE_MAPS_API_KEY = "AIzaSyA6u3OYwIp2_pEn-CE72vFwB1BNNMxT2h4"

# Función para convertir imagen a base64
def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode()

# Función para obtener la dirección a partir de coordenadas
def get_address_from_coordinates(lat, lng):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={GOOGLE_MAPS_API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK":
                return data["results"][0]["formatted_address"]
    except Exception as e:
        st.error(f"Error al obtener la dirección: {e}")
    return "Dirección no disponible"

# Función para agregar un evento a MongoDB
def add_event(lat, lng, address, operation_type, image_base64=None):
    event_data = {
        "lat": lat,
        "lng": lng,
        "address": address,
        "operation_type": operation_type,
        "timestamp": datetime.now().strftime("%b-%d-%Y %I:%M%p"),
        "image": image_base64
    }
    events_collection.insert_one(event_data)

# Configuración de la página
st.set_page_config(page_title="Mapa de Operaciones", page_icon="🚨", layout="wide")
st.title("🚨 Mapa de Operaciones")
st.markdown("Haz clic en el mapa para registrar una ubicación y subir evidencia.")

# Estado para almacenar la ubicación clickeada
if "clicked_location" not in st.session_state:
    st.session_state.clicked_location = None

# Crear mapa centrado en EE.UU.
m = folium.Map(location=[37.0902, -95.7129], zoom_start=4)

# Cargar eventos desde MongoDB
events = list(events_collection.find({}, {"_id": 0}).sort("timestamp", -1))

# Agregar marcadores con imágenes en popups
for event in events:
    lat, lng = event.get("lat"), event.get("lng")
    operation_type = event.get("operation_type", "Sin Tipo")
    address = event.get("address", "Dirección no disponible")
    timestamp = event.get("timestamp", "Fecha no disponible")
    image_base64 = event.get("image")

    # Convertir la fecha al formato deseado
    try:
        timestamp = datetime.strptime(timestamp, "%b-%d-%Y %I:%M%p")
        formatted_timestamp = timestamp.strftime("%b-%d-%Y %I:%M%p")
    except:
        formatted_timestamp = timestamp

    popup_content = f"""
        <b>{operation_type}</b><br>{address}<br><i>{formatted_timestamp}</i>
    """
    
    if image_base64:
        popup_content += f'<br><img src="data:image/png;base64,{image_base64}" width="200">'

    if lat is not None and lng is not None:
        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_content, max_width=250),
            tooltip=f"{operation_type} - {address}",
            icon=folium.Icon(color="red" if operation_type == "Operaciones en Calle" else "blue", icon="info-sign")
        ).add_to(m)

# Mostrar mapa y capturar interacciones
map_data = st_folium(m, width=1000, height=600, key="map")

# Verificar si se ha hecho clic en el mapa
if map_data and "last_clicked" in map_data and map_data["last_clicked"] is not None:
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lng = map_data["last_clicked"]["lng"]
    
    # Guardar la ubicación en sesión para mostrar la ventana emergente
    st.session_state.clicked_location = (clicked_lat, clicked_lng)

# Mostrar la ventana emergente si hay una ubicación guardada
if st.session_state.clicked_location:
    st.markdown("### 📍 Ubicación Seleccionada")
    
    clicked_lat, clicked_lng = st.session_state.clicked_location
    address = get_address_from_coordinates(clicked_lat, clicked_lng)

    operation_type = st.radio("Selecciona el tipo de operación:", ["Operaciones en Calle", "Operaciones en Casa"])

    # Subir imagen (opcional)
    uploaded_file = st.file_uploader("Subir evidencia (opcional)", type=["png", "jpg", "jpeg"])

    image_base64 = encode_image(uploaded_file) if uploaded_file else None

    if st.button("✅ Registrar Ubicación"):
        add_event(clicked_lat, clicked_lng, address, operation_type, image_base64)
        st.success(f"Ubicación registrada: {address} como **{operation_type}**")
        st.session_state.clicked_location = None  # Limpiar la sesión

# Mostrar lista de eventos registrados
st.subheader("📌 Últimos Eventos Registrados")

if events:
    for event in events[:100]:  # Mostrar los últimos 100 eventos
        lat = event.get("lat")
        lng = event.get("lng")
        address = event.get("address", "Dirección no disponible")
        operation_type = event.get("operation_type", "Sin Tipo")
        
        # Convertir la fecha al formato deseado
        timestamp = event.get("timestamp", "Fecha no disponible")
        try:
            timestamp = datetime.strptime(timestamp, "%b-%d-%Y %I:%M%p")
            formatted_timestamp = timestamp.strftime("%b-%d-%Y %I:%M%p")
        except:
            formatted_timestamp = timestamp
        
        # Crear el enlace de Google Maps
        if lat is not None and lng is not None:
            google_maps_link = f"https://www.google.com/maps?q={lat},{lng}"
        else:
            google_maps_link = "#"

        st.write(f"""
        **📅 Fecha y Hora:** {formatted_timestamp}  
        **📍 Dirección:** {address}  
        **🚨 Tipo de Operación:** {operation_type}  
        **🔗 Ver en Mapa:** [Enlace de ubicación]( {google_maps_link} ) 
        """)

        if event.get("image"):
            st.image(f"data:image/png;base64,{event.get('image')}", width=300)
else:
    st.write("No hay eventos registrados aún.")
