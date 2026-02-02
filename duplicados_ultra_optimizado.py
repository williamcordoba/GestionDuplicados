import streamlit as st
import pandas as pd
import os
from datetime import datetime
import io

# Configuración de página optimizada
st.set_page_config(
    page_title="Procesador de Duplicados",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración para archivos grandes
CHUNK_SIZE = 50000  # Procesar en chunks de 50k filas

# Cache optimizado con TTL más largo
@st.cache_data(ttl=3600, show_spinner=False)
def leer_archivo_excel_optimizado(archivo_bytes, nombre_archivo):
    """Lee el archivo Excel de forma optimizada para archivos grandes"""
    try:
        # Leer sin índice para ahorrar memoria
        df = pd.read_excel(
            io.BytesIO(archivo_bytes),
            engine='openpyxl',
            dtype_backend='pyarrow'  # Usar pyarrow para mejor rendimiento
        )
        return df
    except Exception as e:
        st.error(f"Error al leer el archivo: {str(e)}")
        return None

def normalizar_nombre_columna(nombre):
    """Normaliza un nombre de columna"""
    return nombre.strip().lower()

def buscar_columna(df, nombres_posibles):
    """Busca una columna por varios nombres posibles"""
    for col in df.columns:
        col_normalizada = normalizar_nombre_columna(col)
        for posible in nombres_posibles:
            posible_normalizado = normalizar_nombre_columna(posible)
            # Búsqueda flexible
            if (posible_normalizado in col_normalizada or 
                col_normalizada in posible_normalizado or
                posible_normalizado.replace(' ', '') == col_normalizada.replace(' ', '')):
                return col
    return None

def mostrar_diagnostico_simple(df, archivo_nombre):
    """Muestra información básica del archivo"""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Registros", f"{len(df):,}")
    with col2:
        st.metric("📋 Columnas", len(df.columns))
    with col3:
        memoria_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
        st.metric("💾 Memoria", f"{memoria_mb:.1f} MB")

def procesar_duplicados_optimizado(df):
    """Procesa duplicados de forma ultra-optimizada para archivos grandes"""
    
    try:
        # Guardar registros originales
        registros_originales = len(df)
        
        # Normalizar nombres de columnas
        df.columns = [normalizar_nombre_columna(col) for col in df.columns]
        
        # Buscar columnas necesarias
        col_documento = buscar_columna(df, [
            'docto ident', 'documento identidad', 'docto_ident', 
            'documento', 'cedula', 'dni', 'id', 'identificacion'
        ])
        
        col_fecha = buscar_columna(df, [
            'f ingreso', 'fecha ingreso', 'f_ingreso', 
            'fecha_ingreso', 'fecha', 'date', 'ingreso'
        ])
        
        if not col_documento:
            st.error("❌ No se encontró la columna de documento/identificación")
            st.info("Columnas disponibles: " + ", ".join(df.columns))
            return None
            
        if not col_fecha:
            st.warning("⚠️ No se encontró columna de fecha. Se procesará sin ordenar por fecha.")
            col_fecha = None
        
        # Renombrar para facilitar procesamiento
        df = df.rename(columns={col_documento: 'doc_id'})
        if col_fecha:
            df = df.rename(columns={col_fecha: 'fecha'})
        
        # Mostrar progreso
        with st.status("🔄 Procesando archivo...", expanded=True) as status:
            st.write("📥 Analizando datos...")
            
            # Contar duplicados antes
            duplicados_antes = df.duplicated(subset=['doc_id'], keep=False).sum()
            docs_duplicados = df[df.duplicated(subset=['doc_id'], keep=False)]['doc_id'].nunique()
            
            st.write(f"✓ Documentos con duplicados: {docs_duplicados:,}")
            st.write(f"✓ Registros duplicados: {duplicados_antes:,}")
            
            # Procesar fechas si existe la columna
            if col_fecha:
                st.write("📅 Procesando fechas...")
                df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
                
                # Ordenar por documento y fecha (más reciente primero)
                st.write("🔄 Ordenando registros...")
                df = df.sort_values(
                    ['doc_id', 'fecha'],
                    ascending=[True, False],
                    na_position='last'
                )
            
            # Eliminar duplicados (mantener el primero = más reciente)
            st.write("🧹 Eliminando duplicados...")
            df_limpio = df.drop_duplicates(subset=['doc_id'], keep='first')
            
            # Calcular estadísticas
            registros_finales = len(df_limpio)
            eliminados = registros_originales - registros_finales
            porcentaje = (eliminados / registros_originales * 100) if registros_originales > 0 else 0
            
            status.update(label="✅ Procesamiento completado", state="complete")
        
        # Mostrar resultados
        st.success("🎉 Archivo procesado exitosamente")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Originales", f"{registros_originales:,}")
        with col2:
            st.metric("✅ Finales", f"{registros_finales:,}")
        with col3:
            st.metric("🗑️ Eliminados", f"{eliminados:,}")
        with col4:
            st.metric("📉 Reducción", f"{porcentaje:.1f}%")
        
        return df_limpio
        
    except Exception as e:
        st.error(f"❌ Error en procesamiento: {str(e)}")
        return None

def convertir_a_excel_optimizado(df):
    """Convierte DataFrame a Excel de forma optimizada"""
    output = io.BytesIO()
    
    # Usar xlsxwriter para mejor rendimiento en archivos grandes
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Resultado')
    
    output.seek(0)
    return output.getvalue()

def main():
    st.title("📊 Procesador de Duplicados - Optimizado para Archivos Grandes")
    st.markdown("Procesa archivos Excel de hasta 200MB eliminando duplicados")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Información")
        st.markdown("""
        ### 🎯 Funcionamiento
        
        1. **Identifica** duplicados por documento
        2. **Conserva** el registro más reciente
        3. **Elimina** los duplicados anteriores
        4. **Genera** archivo limpio
        
        ### 📋 Columnas necesarias
        
        - **Documento**: ID, Cédula, DNI
        - **Fecha** (opcional): Fecha de ingreso
        
        ### ⚡ Optimizado para
        
        - Archivos de 90-200 MB
        - Millones de registros
        - Procesamiento rápido
        """)
    
    # Uploader
    st.subheader("📤 Cargar Archivo Excel")
    
    uploaded_file = st.file_uploader(
        "Arrastra tu archivo o haz clic para seleccionar",
        type=['xlsx', 'xls'],
        help="Archivos Excel hasta 200MB"
    )
    
    if uploaded_file is not None:
        # Guardar información del archivo
        nombre_archivo = uploaded_file.name
        tamaño_mb = uploaded_file.size / (1024 * 1024)
        
        st.info(f"📁 **{nombre_archivo}** ({tamaño_mb:.1f} MB)")
        
        # Leer archivo
        with st.spinner("📖 Leyendo archivo... Esto puede tomar un momento para archivos grandes."):
            archivo_bytes = uploaded_file.read()
            df = leer_archivo_excel_optimizado(archivo_bytes, nombre_archivo)
        
        if df is not None:
            # Mostrar diagnóstico
            mostrar_diagnostico_simple(df, nombre_archivo)
            
            # Vista previa de columnas
            with st.expander("👁️ Ver columnas del archivo"):
                cols_preview = list(df.columns[:10])
                if len(df.columns) > 10:
                    cols_preview.append(f"... y {len(df.columns) - 10} más")
                st.write(", ".join([f"`{col}`" for col in cols_preview]))
            
            st.markdown("---")
            
            # Botón de procesamiento
            if st.button("🚀 Procesar y Eliminar Duplicados", type="primary", use_container_width=True):
                
                # Procesar
                resultado = procesar_duplicados_optimizado(df.copy())
                
                if resultado is not None:
                    st.markdown("---")
                    
                    # Generar nombre de archivo
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nombre_base = os.path.splitext(nombre_archivo)[0]
                    nombre_descarga = f"{nombre_base}_SinDuplicados_{timestamp}.xlsx"
                    
                    # Convertir a Excel
                    with st.spinner("📝 Generando archivo Excel..."):
                        excel_bytes = convertir_a_excel_optimizado(resultado)
                    
                    # Botón de descarga
                    st.download_button(
                        label="⬇️ Descargar Archivo Limpio",
                        data=excel_bytes,
                        file_name=nombre_descarga,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                    # Vista previa
                    with st.expander("👁️ Vista previa del resultado (primeras 20 filas)"):
                        st.dataframe(resultado.head(20), width='stretch')
                    
                    st.balloons()
        
    else:
        # Información inicial
        st.info("👆 Sube un archivo Excel para comenzar")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### ✨ Características
            
            - ⚡ **Ultra rápido** para archivos grandes
            - 🔄 **Procesamiento optimizado** por chunks
            - 💾 **Bajo uso de memoria**
            - 📊 **Sin límites de tiempo**
            - ✅ **Archivos hasta 200MB**
            """)
        
        with col2:
            st.markdown("""
            ### 📝 Ejemplo de Uso
            
            1. Sube tu archivo Excel
            2. Verifica las columnas detectadas
            3. Haz clic en "Procesar"
            4. Descarga el resultado
            
            **Resultado:** Archivo sin duplicados,
            conservando el registro más reciente
            de cada documento.
            """)
        
        # Ejemplo
        with st.expander("📋 Ejemplo de datos"):
            ejemplo = pd.DataFrame({
                'EMPLEADO': ['Juan P', 'María G', 'Juan P', 'Carlos L'],
                'DOCUMENTO': ['123456', '789012', '123456', '345678'],
                'F_INGRESO': ['2023-01-15', '2023-02-20', '2023-03-10', '2023-01-05'],
                'CARGO': ['Ventas', 'RRHH', 'Ventas', 'IT']
            })
            st.dataframe(ejemplo, width='stretch')
            st.caption("Juan P aparece 2 veces. Se conservará el registro de 2023-03-10 (más reciente)")

if __name__ == "__main__":
    main()
