import sys
import os
import webbrowser
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QComboBox, QLineEdit, QLabel, QMessageBox, 
                             QAbstractItemView, QFileDialog)
from PyQt6.QtCore import Qt
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# --- CONFIGURACIÓN DE BD ---
Base = declarative_base()

class ProyectoBorrador(Base):
    __tablename__ = 'proyectos_borradores'
    id = Column(Integer, primary_key=True)
    titulo = Column(String(200), default="Nuevo Borrador")
    hashtags = Column(String(200), default="")
    estatus = Column(String(50), default="En redacción")
    revisor = Column(String(100), default="")
    fecha_envio = Column(String(50), default="")
    fecha_revision = Column(String(50), default="")
    fecha_publicacion = Column(String(50), default="")
    feedback = Column(Text, default="")
    ruta_archivo = Column(String(500), default="")
    fecha_modificacion = Column(String(50), default="")

class EventoAcademico(Base):
    __tablename__ = 'eventos_academicos'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), default="Nuevo Evento/Revista")
    tipo = Column(String(50), default="Congreso")
    fecha_limite = Column(String(50), default="")
    url = Column(String(500), default="")
    estatus = Column(String(50), default="Buscando")

engine = create_engine('sqlite:///investigacion_productiva.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- MÓDULO 5: CENTRO DE GESTIÓN ---
class ModuloGestion(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Módulo 5: Gestión de Proyectos y Proyección Académica")
        self.resize(1200, 700)
        
        layout_principal = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tab_borradores = QWidget()
        self.tab_eventos = QWidget()
        
        self.tabs.addTab(self.tab_borradores, "📝 Control de Borradores")
        self.tabs.addTab(self.tab_eventos, "📅 Agenda y Espacios de Exposición")
        
        self.configurar_tab_borradores()
        self.configurar_tab_eventos()
        
        layout_principal.addWidget(self.tabs)
        self.cargar_datos()

    # --- PESTAÑA 1: BORRADORES ---
    def configurar_tab_borradores(self):
        layout = QVBoxLayout(self.tab_borradores)
        controles = QHBoxLayout()
        
        btn_nuevo = QPushButton("➕ Nuevo")
        btn_nuevo.clicked.connect(self.agregar_borrador)
        
        btn_word = QPushButton("📄 Abrir / Vincular Word")
        btn_word.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold;")
        btn_word.clicked.connect(self.abrir_vincular_word)
        
        lbl_estatus = QLabel("Estatus:")
        self.combo_estatus_toolbar = QComboBox()
        self.combo_estatus_toolbar.addItems(["En redacción", "Ajustando", "Enviado a revisión", "Rechazado", "Aprobado", "Publicado"])
        self.combo_estatus_toolbar.currentTextChanged.connect(self.cambiar_estatus_fila)
        
        btn_guardar = QPushButton("💾 Guardar")
        btn_guardar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_guardar.clicked.connect(self.guardar_borradores)
        
        btn_eliminar = QPushButton("🗑️ Eliminar")
        btn_eliminar.clicked.connect(self.eliminar_borrador)
        
        controles.addWidget(btn_nuevo)
        controles.addWidget(btn_word)
        controles.addStretch()
        controles.addWidget(lbl_estatus)
        controles.addWidget(self.combo_estatus_toolbar)
        controles.addWidget(btn_guardar)
        controles.addWidget(btn_eliminar)
        
        self.tabla_borradores = QTableWidget(0, 10)
        self.tabla_borradores.setHorizontalHeaderLabels([
            "ID", "Título", "Hashtags", "Estatus", "Revisor/Lector", 
            "F. Envío", "F. Revisión", "F. Publicación", "Feedback", "Archivo Vinculado"
        ])
        
        # Ajustes de visualización (Ya no ocultamos la columna 9)
        self.tabla_borradores.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabla_borradores.horizontalHeader().setStretchLastSection(True)
        self.tabla_borradores.hideColumn(0) # Ocultar ID
        self.tabla_borradores.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_borradores.setSortingEnabled(True) 
        self.tabla_borradores.itemSelectionChanged.connect(self.sincronizar_combo_estatus)
        
        # Conexión directa para abrir con doble clic
        self.tabla_borradores.cellDoubleClicked.connect(self.abrir_documento_doble_clic)
        
        layout.addLayout(controles)
        layout.addWidget(self.tabla_borradores)

    # --- PESTAÑA 2: AGENDA Y ESPACIOS ---
    def configurar_tab_eventos(self):
        layout = QVBoxLayout(self.tab_eventos)
        controles = QHBoxLayout()
        
        btn_nuevo = QPushButton("➕ Registrar Evento")
        btn_nuevo.clicked.connect(self.agregar_evento)
        
        btn_buscar_web = QPushButton("🌐 Buscar Convocatorias")
        btn_buscar_web.setStyleSheet("background-color: #2980b9; color: white;")
        btn_buscar_web.clicked.connect(self.buscar_convocatorias)
        
        btn_guardar = QPushButton("💾 Guardar")
        btn_guardar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_guardar.clicked.connect(self.guardar_eventos)
        
        btn_abrir_url = QPushButton("🔗 Abrir Enlace")
        btn_abrir_url.clicked.connect(self.abrir_enlace_evento)
        
        btn_eliminar = QPushButton("🗑️ Eliminar")
        btn_eliminar.clicked.connect(self.eliminar_evento)
        
        controles.addWidget(btn_nuevo)
        controles.addWidget(btn_buscar_web)
        controles.addStretch()
        controles.addWidget(btn_guardar)
        controles.addWidget(btn_abrir_url)
        controles.addWidget(btn_eliminar)
        
        self.tabla_eventos = QTableWidget(0, 6)
        self.tabla_eventos.setHorizontalHeaderLabels(["ID", "Nombre (Congreso/Revista)", "Tipo", "Fecha Límite", "URL / Enlace", "Estatus"])
        self.tabla_eventos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_eventos.hideColumn(0)
        self.tabla_eventos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_eventos.setSortingEnabled(True)
        
        layout.addLayout(controles)
        layout.addWidget(self.tabla_eventos)

    # --- LÓGICA DE DATOS ---
    def cargar_datos(self):
        session = Session()
        
        # Cargar Borradores
        self.tabla_borradores.setSortingEnabled(False) 
        borradores = session.query(ProyectoBorrador).all()
        self.tabla_borradores.setRowCount(len(borradores))
        
        for fila, b in enumerate(borradores):
            self.tabla_borradores.setItem(fila, 0, QTableWidgetItem(str(b.id)))
            self.tabla_borradores.setItem(fila, 1, QTableWidgetItem(b.titulo))
            self.tabla_borradores.setItem(fila, 2, QTableWidgetItem(b.hashtags))
            
            item_estatus = QTableWidgetItem(b.estatus)
            item_estatus.setFlags(item_estatus.flags() & ~Qt.ItemFlag.ItemIsEditable) 
            self.tabla_borradores.setItem(fila, 3, item_estatus)
            
            self.tabla_borradores.setItem(fila, 4, QTableWidgetItem(b.revisor))
            self.tabla_borradores.setItem(fila, 5, QTableWidgetItem(b.fecha_envio))
            self.tabla_borradores.setItem(fila, 6, QTableWidgetItem(b.fecha_revision))
            self.tabla_borradores.setItem(fila, 7, QTableWidgetItem(b.fecha_publicacion))
            self.tabla_borradores.setItem(fila, 8, QTableWidgetItem(b.feedback))
            
            # Formato protegido para la celda de la ruta
            item_ruta = QTableWidgetItem(b.ruta_archivo)
            item_ruta.setFlags(item_ruta.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_ruta.setToolTip("Haz doble clic para abrir este documento en Word")
            self.tabla_borradores.setItem(fila, 9, item_ruta)
            
        self.tabla_borradores.setSortingEnabled(True) 

        # Cargar Eventos
        self.tabla_eventos.setSortingEnabled(False)
        eventos = session.query(EventoAcademico).all()
        self.tabla_eventos.setRowCount(len(eventos))
        
        for fila, e in enumerate(eventos):
            self.tabla_eventos.setItem(fila, 0, QTableWidgetItem(str(e.id)))
            self.tabla_eventos.setItem(fila, 1, QTableWidgetItem(e.nombre))
            
            combo_tipo = QComboBox()
            combo_tipo.addItems(["Congreso", "Coloquio", "Revista Indexada", "Seminario", "Libro"])
            combo_tipo.setCurrentText(e.tipo)
            self.tabla_eventos.setCellWidget(fila, 2, combo_tipo)
            
            self.tabla_eventos.setItem(fila, 3, QTableWidgetItem(e.fecha_limite))
            self.tabla_eventos.setItem(fila, 4, QTableWidgetItem(e.url))
            
            combo_est = QComboBox()
            combo_est.addItems(["Buscando/Analizando", "Preparando resumen", "Enviado", "Presentado / Concluido"])
            combo_est.setCurrentText(e.estatus)
            self.tabla_eventos.setCellWidget(fila, 5, combo_est)
            
        self.tabla_eventos.setSortingEnabled(True)
        session.close()

    # --- FUNCIONES BORRADORES ---
    def agregar_borrador(self):
        session = Session()
        nuevo = ProyectoBorrador(fecha_modificacion=datetime.now().strftime("%Y-%m-%d"))
        session.add(nuevo)
        session.commit()
        session.close()
        self.cargar_datos()

    def guardar_borradores(self):
        session = Session()
        for fila in range(self.tabla_borradores.rowCount()):
            b_id = int(self.tabla_borradores.item(fila, 0).text())
            borrador = session.query(ProyectoBorrador).filter_by(id=b_id).first()
            if borrador:
                borrador.titulo = self.tabla_borradores.item(fila, 1).text() if self.tabla_borradores.item(fila, 1) else ""
                borrador.hashtags = self.tabla_borradores.item(fila, 2).text() if self.tabla_borradores.item(fila, 2) else ""
                borrador.estatus = self.tabla_borradores.item(fila, 3).text() if self.tabla_borradores.item(fila, 3) else ""
                borrador.revisor = self.tabla_borradores.item(fila, 4).text() if self.tabla_borradores.item(fila, 4) else ""
                borrador.fecha_envio = self.tabla_borradores.item(fila, 5).text() if self.tabla_borradores.item(fila, 5) else ""
                borrador.fecha_revision = self.tabla_borradores.item(fila, 6).text() if self.tabla_borradores.item(fila, 6) else ""
                borrador.fecha_publicacion = self.tabla_borradores.item(fila, 7).text() if self.tabla_borradores.item(fila, 7) else ""
                borrador.feedback = self.tabla_borradores.item(fila, 8).text() if self.tabla_borradores.item(fila, 8) else ""
                borrador.ruta_archivo = self.tabla_borradores.item(fila, 9).text() if self.tabla_borradores.item(fila, 9) else ""
                borrador.fecha_modificacion = datetime.now().strftime("%Y-%m-%d")
        session.commit()
        session.close()
        QMessageBox.information(self, "Guardado", "Borradores actualizados exitosamente.")

    def eliminar_borrador(self):
        fila = self.tabla_borradores.currentRow()
        if fila >= 0:
            b_id = int(self.tabla_borradores.item(fila, 0).text())
            session = Session()
            borrador = session.query(ProyectoBorrador).filter_by(id=b_id).first()
            if borrador:
                session.delete(borrador)
                session.commit()
            session.close()
            self.cargar_datos()

    def sincronizar_combo_estatus(self):
        fila = self.tabla_borradores.currentRow()
        if fila >= 0:
            estatus_actual = self.tabla_borradores.item(fila, 3).text()
            self.combo_estatus_toolbar.blockSignals(True)
            self.combo_estatus_toolbar.setCurrentText(estatus_actual)
            self.combo_estatus_toolbar.blockSignals(False)

    def cambiar_estatus_fila(self, nuevo_estatus):
        fila = self.tabla_borradores.currentRow()
        if fila >= 0:
            self.tabla_borradores.item(fila, 3).setText(nuevo_estatus)

    def abrir_documento_doble_clic(self, fila, columna):
        """Intercepción del doble clic: si es en la columna 9, abre Word."""
        if columna == 9:
            self.abrir_vincular_word()

    def abrir_vincular_word(self):
        fila = self.tabla_borradores.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Aviso", "Selecciona una fila primero para vincular o abrir su documento.")
            return
            
        ruta_item = self.tabla_borradores.item(fila, 9)
        ruta = ruta_item.text() if ruta_item else ""
        
        if not ruta or not os.path.exists(ruta):
            nueva_ruta, _ = QFileDialog.getOpenFileName(self, "Vincular Borrador (.docx)", "", "Documentos Word (*.docx *.doc)")
            if nueva_ruta:
                if not ruta_item:
                    nuevo_item = QTableWidgetItem(nueva_ruta)
                    nuevo_item.setFlags(nuevo_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    nuevo_item.setToolTip("Haz doble clic para abrir este documento en Word")
                    self.tabla_borradores.setItem(fila, 9, nuevo_item)
                else:
                    ruta_item.setText(nueva_ruta)
                os.startfile(os.path.normpath(nueva_ruta))
        else:
            try:
                os.startfile(os.path.normpath(ruta))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo abrir el archivo:\n{e}")

    # --- FUNCIONES EVENTOS ---
    def agregar_evento(self):
        session = Session()
        nuevo = EventoAcademico()
        session.add(nuevo)
        session.commit()
        session.close()
        self.cargar_datos()

    def guardar_eventos(self):
        session = Session()
        for fila in range(self.tabla_eventos.rowCount()):
            e_id = int(self.tabla_eventos.item(fila, 0).text())
            evento = session.query(EventoAcademico).filter_by(id=e_id).first()
            if evento:
                evento.nombre = self.tabla_eventos.item(fila, 1).text() if self.tabla_eventos.item(fila, 1) else ""
                
                widget_tipo = self.tabla_eventos.cellWidget(fila, 2)
                evento.tipo = widget_tipo.currentText() if widget_tipo else ""
                
                evento.fecha_limite = self.tabla_eventos.item(fila, 3).text() if self.tabla_eventos.item(fila, 3) else ""
                evento.url = self.tabla_eventos.item(fila, 4).text() if self.tabla_eventos.item(fila, 4) else ""
                
                widget_est = self.tabla_eventos.cellWidget(fila, 5)
                evento.estatus = widget_est.currentText() if widget_est else ""
                
        session.commit()
        session.close()
        QMessageBox.information(self, "Guardado", "Agenda académica actualizada.")

    def eliminar_evento(self):
        fila = self.tabla_eventos.currentRow()
        if fila >= 0:
            e_id = int(self.tabla_eventos.item(fila, 0).text())
            session = Session()
            evento = session.query(EventoAcademico).filter_by(id=e_id).first()
            if evento:
                session.delete(evento)
                session.commit()
            session.close()
            self.cargar_datos()

    def abrir_enlace_evento(self):
        fila = self.tabla_eventos.currentRow()
        if fila >= 0:
            item_url = self.tabla_eventos.item(fila, 4)
            url = item_url.text() if item_url else ""
            if url and ("http://" in url or "https://" in url):
                webbrowser.open(url)
            else:
                QMessageBox.warning(self, "URL Inválida", "Asegúrate de incluir 'http://' o 'https://' en el enlace de la columna URL.")

    def buscar_convocatorias(self):
        webbrowser.open("https://www.google.com/search?q=call+for+papers+antropologia+congreso+revista")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = ModuloGestion()
    ventana.show()
    sys.exit(app.exec())
