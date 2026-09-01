import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QLineEdit, QHeaderView, QFileDialog, QMessageBox, QLabel)
from PyQt6.QtCore import Qt
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# --- CONFIGURACIÓN DE BASE DE DATOS LOCAL ---
Base = declarative_base()

class Fuente(Base):
    __tablename__ = 'fuentes'
    id = Column(Integer, primary_key=True)
    titulo = Column(String(200), nullable=False)
    autor = Column(String(100))
    ruta_archivo = Column(String(500)) 

engine = create_engine('sqlite:///investigacion_productiva.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- MÓDULO VISUAL: MATERIAL DE TRABAJO ---
class ModuloMaterialTrabajo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Módulo 1: Material de Trabajo")
        self.resize(900, 500)
        
        self.layout_principal = QVBoxLayout(self)
        
        # --- Barra Superior ---
        self.layout_superior = QHBoxLayout()
        
        self.lbl_titulo = QLabel("Catálogo de Material de Trabajo")
        self.lbl_titulo.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("🔍 Buscar por título o autor...")
        self.buscador.textChanged.connect(self.cargar_datos)
        
        self.btn_agregar = QPushButton("➕ Agregar Archivo Local")
        self.btn_agregar.clicked.connect(self.agregar_fuente)
        self.btn_agregar.setStyleSheet("background-color: #2980b9; color: white; padding: 6px; border-radius: 4px; font-weight: bold;")
        
        self.layout_superior.addWidget(self.lbl_titulo)
        self.layout_superior.addStretch()
        self.layout_superior.addWidget(self.buscador)
        self.layout_superior.addWidget(self.btn_agregar)
        
        # --- Tabla de Fuentes ---
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["ID", "Título", "Escrito por", "Ruta del Archivo"])
        
        # 1. Pestañas/Columnas Ajustables
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabla.horizontalHeader().resizeSection(0, 50)  # ID
        self.tabla.horizontalHeader().resizeSection(1, 300) # Título
        self.tabla.horizontalHeader().resizeSection(2, 200) # Escrito por
        self.tabla.horizontalHeader().setStretchLastSection(True) # La ruta ocupa el resto
        
        # Selección por fila completa (aunque editemos celdas individuales)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # 2. Ordenamiento habilitado
        self.tabla.setSortingEnabled(True)
        
        # Conectar el evento de edición de celda para actualizar la base de datos
        self.tabla.itemChanged.connect(self.guardar_edicion)
        
        # --- Barra Inferior ---
        self.layout_inferior = QHBoxLayout()
        self.btn_abrir = QPushButton("📂 Abrir Archivo Seleccionado")
        self.btn_abrir.clicked.connect(self.abrir_archivo)
        
        self.btn_eliminar = QPushButton("🗑️ Eliminar Registro")
        self.btn_eliminar.clicked.connect(self.eliminar_fuente)
        self.btn_eliminar.setStyleSheet("background-color: #c0392b; color: white; padding: 6px; border-radius: 4px; font-weight: bold;")
        
        self.layout_inferior.addWidget(self.btn_abrir)
        self.layout_inferior.addStretch()
        self.layout_inferior.addWidget(self.btn_eliminar)
        
        self.layout_principal.addLayout(self.layout_superior)
        self.layout_principal.addWidget(self.tabla)
        self.layout_principal.addLayout(self.layout_inferior)
        
        self.cargar_datos()

    def cargar_datos(self):
        """Llena la tabla evitando disparar el evento de edición durante la carga."""
        texto_busqueda = self.buscador.text().lower()
        session = Session()
        
        query = session.query(Fuente)
        if texto_busqueda:
            query = query.filter(
                (Fuente.titulo.ilike(f"%{texto_busqueda}%")) | 
                (Fuente.autor.ilike(f"%{texto_busqueda}%"))
            )
        fuentes = query.all()
        session.close()
        
        # Bloqueamos señales y ordenamiento mientras construimos la tabla para evitar errores
        self.tabla.blockSignals(True)
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(0)
        
        for fila, fuente in enumerate(fuentes):
            self.tabla.insertRow(fila)
            
            # ID (No editable)
            item_id = QTableWidgetItem(str(fuente.id))
            item_id.setFlags(item_id.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Título y Autor (Editables)
            item_titulo = QTableWidgetItem(fuente.titulo)
            item_autor = QTableWidgetItem(fuente.autor or "Por definir")
            
            # Ruta (No editable desde la tabla)
            item_ruta = QTableWidgetItem(fuente.ruta_archivo)
            item_ruta.setFlags(item_ruta.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            self.tabla.setItem(fila, 0, item_id)
            self.tabla.setItem(fila, 1, item_titulo)
            self.tabla.setItem(fila, 2, item_autor)
            self.tabla.setItem(fila, 3, item_ruta)
            
        self.tabla.setSortingEnabled(True)
        self.tabla.blockSignals(False)

    def guardar_edicion(self, item):
        """Se dispara automáticamente al terminar de editar una celda y guarda en BD."""
        fila = item.row()
        columna = item.column()
        
        id_item = self.tabla.item(fila, 0)
        if not id_item: return
        
        fuente_id = int(id_item.text())
        nuevo_valor = item.text()
        
        session = Session()
        fuente = session.query(Fuente).filter(Fuente.id == fuente_id).first()
        
        if fuente:
            if columna == 1: # Si editó el Título
                fuente.titulo = nuevo_valor
            elif columna == 2: # Si editó "Escrito por"
                fuente.autor = nuevo_valor
            session.commit()
            
        session.close()

    def agregar_fuente(self):
        ruta_archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar Material de Lectura", "", "Documentos (*.pdf *.docx *.epub *.txt);;Todos (*)")
        if ruta_archivo:
            nombre_base = os.path.basename(ruta_archivo)
            titulo_defecto = os.path.splitext(nombre_base)[0].replace("_", " ").title()
            
            session = Session()
            nueva_fuente = Fuente(titulo=titulo_defecto, autor="Por definir", ruta_archivo=ruta_archivo)
            session.add(nueva_fuente)
            session.commit()
            session.close()
            self.cargar_datos()

    def abrir_archivo(self):
        fila_actual = self.tabla.currentRow()
        if fila_actual >= 0:
            ruta = self.tabla.item(fila_actual, 3).text()
            if os.path.exists(ruta):
                try: os.startfile(ruta)
                except Exception as e: QMessageBox.warning(self, "Error", f"No se pudo abrir el archivo: {e}")
            else:
                QMessageBox.warning(self, "Error", "El archivo no se encuentra en la ruta registrada.")
        else:
            QMessageBox.information(self, "Aviso", "Selecciona un material de la tabla primero.")

    def eliminar_fuente(self):
        fila_actual = self.tabla.currentRow()
        if fila_actual >= 0:
            id_fuente = self.tabla.item(fila_actual, 0).text()
            respuesta = QMessageBox.question(self, "Confirmar", "¿Seguro que deseas eliminar este registro del catálogo?", 
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if respuesta == QMessageBox.StandardButton.Yes:
                session = Session()
                fuente = session.query(Fuente).filter(Fuente.id == id_fuente).first()
                if fuente:
                    session.delete(fuente)
                    session.commit()
                session.close()
                self.cargar_datos()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = ModuloMaterialTrabajo()
    ventana.show()
    sys.exit(app.exec())
