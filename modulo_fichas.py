import sys
import fitz 
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QTextEdit, QListWidget, 
                             QSplitter, QMessageBox, QLabel, QListWidgetItem,
                             QLineEdit, QFormLayout, QDialog, QMenu, QCompleter, QScrollArea)
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QPixmap
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# --- CONFIGURACIÓN DE BASE DE DATOS LOCAL ---
Base = declarative_base()

class Fuente(Base):
    __tablename__ = 'fuentes'
    id = Column(Integer, primary_key=True)
    titulo = Column(String(200), nullable=False)
    autor = Column(String(100))
    ruta_archivo = Column(String(500)) 
    fichas = relationship("Ficha", back_populates="fuente")

class Ficha(Base):
    __tablename__ = 'fichas'
    id = Column(Integer, primary_key=True)
    fuente_id = Column(Integer, ForeignKey('fuentes.id'))
    titulo = Column(String(150))          
    pagina = Column(String(20))           
    hashtags = Column(String(200))        
    contenido_atomico = Column(Text, nullable=False)
    fuente = relationship("Fuente", back_populates="fichas")

engine = create_engine('sqlite:///investigacion_productiva.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- CLASES PERSONALIZADAS DE UI ---

class MultiCompleter(QCompleter):
    """Autocompletador que permite múltiples sugerencias separadas por espacio en un mismo QLineEdit."""
    def pathFromIndex(self, index):
        path = super().pathFromIndex(index)
        texto = self.widget().text()
        # Conservar todo lo que está antes de la última palabra
        prefijo = texto[:texto.rfind(' ')+1] if ' ' in texto else ''
        return prefijo + path
        
    def splitPath(self, path):
        # Filtra la base de datos usando solo la última palabra que se está escribiendo
        return [path.split(' ')[-1]]

class VisorImagenZoom(QScrollArea):
    """Visor de imágenes interactivo con soporte de Zoom mediante Ctrl + Rueda."""
    def __init__(self, pixmap):
        super().__init__()
        self.factor_zoom = 1.0
        
        # Redimensiona la imagen si es demasiado grande para estabilizar la ventana inicial
        if pixmap.width() > 1000 or pixmap.height() > 1000:
            self.pixmap_original = pixmap.scaled(900, 900, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            self.pixmap_original = pixmap

        self.lbl_img = QLabel()
        self.lbl_img.setPixmap(self.pixmap_original)
        self.lbl_img.setScaledContents(True) 
        self.lbl_img.resize(self.pixmap_original.size())
        
        self.setWidget(self.lbl_img)
        self.setWidgetResizable(False) 
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Zoom In / Out
            if event.angleDelta().y() > 0:
                self.factor_zoom *= 1.15
            else:
                self.factor_zoom /= 1.15
            
            # Aplicar límites de zoom
            if self.factor_zoom > 6.0: self.factor_zoom = 6.0
            if self.factor_zoom < 0.2: self.factor_zoom = 0.2
            
            w = int(self.pixmap_original.width() * self.factor_zoom)
            h = int(self.pixmap_original.height() * self.factor_zoom)
            self.lbl_img.resize(w, h)
        else:
            super().wheelEvent(event) # Permite desplazamiento vertical normal si no se usa Ctrl

# --- VENTANA EMERGENTE DE TRANSCRIPCIÓN ---
class VentanaTranscripcion(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modo Transcripción Visual")
        self.resize(1000, 650)
        
        # Habilitar los controles completos de la ventana (Maximizar, Minimizar, Cerrar)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        
        layout = QHBoxLayout(self)

        # Visor con Zoom (Izquierda)
        layout_izquierdo = QVBoxLayout()
        self.visor_zoom = VisorImagenZoom(pixmap)
        lbl_instruccion_zoom = QLabel("<i>(Mantén <b>Ctrl + Rueda del ratón</b> para hacer zoom)</i>")
        lbl_instruccion_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_izquierdo.addWidget(self.visor_zoom)
        layout_izquierdo.addWidget(lbl_instruccion_zoom)
        
        # Editor (Derecha)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Transcribe aquí el texto de la imagen...\n\nSi es un esquema, puedes describirlo.")
        self.editor.setStyleSheet("font-size: 14px; padding: 10px;")
        
        layout_derecho = QVBoxLayout()
        layout_derecho.addWidget(QLabel("<b>Transcripción Manual:</b>"))
        layout_derecho.addWidget(self.editor)
        
        self.btn_finalizar = QPushButton("Terminar y Extraer como Ficha ➔")
        self.btn_finalizar.setStyleSheet("background-color: #2980b9; color: white; padding: 10px; font-weight: bold;")
        self.btn_finalizar.clicked.connect(self.accept)
        layout_derecho.addWidget(self.btn_finalizar)

        # El parámetro "1" asegura que ambos paneles crezcan proporcionalmente al maximizar
        layout.addLayout(layout_izquierdo, 1)
        layout.addLayout(layout_derecho, 1)

    def obtener_texto(self):
        return self.editor.toPlainText()

# --- MÓDULO VISUAL PRINCIPAL ---
class ModuloNotasReferencia(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Módulo 2: Comprensión, Condensación y Atomización")
        self.resize(1150, 650)
        
        layout_principal = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ==========================================
        # PANEL IZQUIERDO: MATERIAL ORIGEN Y LECTURA
        # ==========================================
        panel_izquierdo = QWidget()
        layout_izq = QVBoxLayout(panel_izquierdo)
        layout_izq.setContentsMargins(0, 0, 10, 0)
        
        self.lbl_fuente = QLabel("1. Material de Trabajo:")
        self.lbl_fuente.setStyleSheet("font-weight: bold;")
        self.combo_fuentes = QComboBox()
        self.combo_fuentes.currentIndexChanged.connect(self.cargar_fichas_de_fuente)
        
        layout_importacion = QHBoxLayout()
        self.btn_cargar_pdf = QPushButton("📄 Cargar Texto del Archivo")
        self.btn_cargar_pdf.clicked.connect(self.extraer_texto_directo)
        
        self.btn_transcribir = QPushButton("🖼️ Transcribir Portapapeles")
        self.btn_transcribir.setStyleSheet("background-color: #8e44ad; color: white;")
        self.btn_transcribir.clicked.connect(self.abrir_transcripcion_portapapeles)
        
        layout_importacion.addWidget(self.btn_cargar_pdf)
        layout_importacion.addWidget(self.btn_transcribir)
        
        self.area_lectura = QTextEdit()
        self.area_lectura.setPlaceholderText("El texto de tus documentos se cargará aquí.\n\nSelecciona el texto importante y presiona el botón verde de abajo para extraerlo.")
        
        self.btn_extraer = QPushButton("Extraer selección a nueva Ficha ➔")
        self.btn_extraer.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold; border-radius: 4px;")
        self.btn_extraer.clicked.connect(self.extraer_a_ficha)
        
        layout_izq.addWidget(self.lbl_fuente)
        layout_izq.addWidget(self.combo_fuentes)
        layout_izq.addLayout(layout_importacion)
        layout_izq.addWidget(self.area_lectura)
        layout_izq.addWidget(self.btn_extraer)
        
        # ==========================================
        # PANEL DERECHO: FICHAS ATÓMICAS Y METADATOS
        # ==========================================
        panel_derecho = QWidget()
        layout_der = QVBoxLayout(panel_derecho)
        layout_der.setContentsMargins(10, 0, 0, 0)
        
        self.lbl_fichas = QLabel("2. Fichas Atómicas Extraídas:")
        self.lbl_fichas.setStyleSheet("font-weight: bold;")
        self.lista_fichas = QListWidget()
        self.lista_fichas.setMaximumHeight(150) 
        self.lista_fichas.itemClicked.connect(self.mostrar_contenido_ficha)
        
        # Formulario de Metadatos
        form_layout = QFormLayout()
        self.in_titulo = QLineEdit()
        self.in_titulo.setPlaceholderText("Ej. Definición de Poder")
        
        self.in_pagina = QLineEdit()
        self.in_pagina.setPlaceholderText("Ej. 45")
        
        layout_hashtags = QHBoxLayout()
        self.in_hashtags = QLineEdit()
        self.in_hashtags.setPlaceholderText("Ej. #teoría #estado (Escribe y autocompleta)")
        
        # Configuración del Autocompletador Dinámico
        self.completer_hashtags = MultiCompleter()
        self.completer_hashtags.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer_hashtags.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.in_hashtags.setCompleter(self.completer_hashtags)
        
        self.btn_hashtags = QPushButton("🏷️ Usados")
        self.btn_hashtags.clicked.connect(self.mostrar_menu_hashtags)
        layout_hashtags.addWidget(self.in_hashtags)
        layout_hashtags.addWidget(self.btn_hashtags)
        
        form_layout.addRow("Título breve:", self.in_titulo)
        form_layout.addRow("Página(s):", self.in_pagina)
        form_layout.addRow("Hashtags:", layout_hashtags)
        
        self.area_edicion_ficha = QTextEdit()
        self.area_edicion_ficha.setPlaceholderText("Contenido de la cita o apunte atómico...")
        
        # Controles de Guardado
        layout_controles_ficha = QHBoxLayout()
        self.btn_guardar_ficha = QPushButton("💾 Guardar Cambios")
        self.btn_guardar_ficha.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold;")
        self.btn_guardar_ficha.clicked.connect(self.guardar_edicion_ficha)
        
        self.btn_eliminar_ficha = QPushButton("🗑️ Eliminar")
        self.btn_eliminar_ficha.setStyleSheet("background-color: #c0392b; color: white;")
        self.btn_eliminar_ficha.clicked.connect(self.eliminar_ficha)
        
        layout_controles_ficha.addWidget(self.btn_guardar_ficha)
        layout_controles_ficha.addWidget(self.btn_eliminar_ficha)
        
        layout_der.addWidget(self.lbl_fichas)
        layout_der.addLayout(form_layout)
        layout_der.addWidget(self.area_edicion_ficha)
        layout_der.addLayout(layout_controles_ficha)
        
        splitter.addWidget(panel_izquierdo)
        splitter.addWidget(panel_derecho)
        splitter.setSizes([550, 550]) 
        layout_principal.addWidget(splitter)
        
        self.cargar_fuentes()
        self.actualizar_memoria_hashtags() # Cargar sugerencias al iniciar

    def actualizar_memoria_hashtags(self):
        """Extrae todos los hashtags de la BD y los inyecta en el QCompleter."""
        session = Session()
        fichas = session.query(Ficha.hashtags).filter(Ficha.hashtags != "").all()
        session.close()
        
        tags_unicos = set()
        for f in fichas:
            if f.hashtags:
                tags_unicos.update([t.strip() for t in f.hashtags.split() if t.strip()])
                
        self.completer_hashtags.setModel(QStringListModel(sorted(tags_unicos)))

    def cargar_fuentes(self):
        self.combo_fuentes.blockSignals(True)
        self.combo_fuentes.clear()
        session = Session()
        fuentes = session.query(Fuente).all()
        for fuente in fuentes:
            self.combo_fuentes.addItem(f"{fuente.titulo}", userData=fuente.id)
        session.close()
        self.combo_fuentes.blockSignals(False)
        if self.combo_fuentes.count() > 0:
            self.cargar_fichas_de_fuente()

    def extraer_texto_directo(self):
        fuente_id = self.combo_fuentes.currentData()
        if not fuente_id: return
        session = Session()
        fuente = session.query(Fuente).filter(Fuente.id == fuente_id).first()
        ruta = fuente.ruta_archivo if fuente else ""
        session.close()

        if ruta.endswith('.pdf'):
            try:
                doc = fitz.open(ruta)
                texto_completo = "".join([f"\n\n--- [PÁGINA {i}] ---\n\n{p.get_text()}" for i, p in enumerate(doc, start=1)])
                self.area_lectura.setPlainText(texto_completo)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo leer el PDF: {e}")
        elif ruta.endswith('.txt'):
            with open(ruta, 'r', encoding='utf-8') as f:
                self.area_lectura.setPlainText(f.read())

    def abrir_transcripcion_portapapeles(self):
        fuente_id = self.combo_fuentes.currentData()
        if not fuente_id:
            QMessageBox.warning(self, "Aviso", "Selecciona un material de trabajo primero.")
            return

        portapapeles = QApplication.clipboard()
        mime_data = portapapeles.mimeData()
        
        if mime_data.hasImage():
            dialogo = VentanaTranscripcion(portapapeles.pixmap(), self)
            if dialogo.exec() == QDialog.DialogCode.Accepted:
                texto_transcrito = dialogo.obtener_texto().strip()
                if texto_transcrito:
                    self.crear_y_seleccionar_ficha(fuente_id, texto_transcrito, "Transcripción Visual")
        else:
            QMessageBox.warning(self, "Aviso", "Copia una imagen al portapapeles primero.")

    def extraer_a_ficha(self):
        texto_seleccionado = self.area_lectura.textCursor().selectedText()
        fuente_id = self.combo_fuentes.currentData()
        
        if not fuente_id or not texto_seleccionado.strip():
            QMessageBox.information(self, "Aviso", "Selecciona un texto en el panel izquierdo.")
            return
            
        texto_limpio = texto_seleccionado.replace('\u2029', '\n')
        self.crear_y_seleccionar_ficha(fuente_id, texto_limpio, "Nueva Ficha")

    def crear_y_seleccionar_ficha(self, fuente_id, contenido, titulo_defecto):
        session = Session()
        nueva_ficha = Ficha(fuente_id=fuente_id, contenido_atomico=contenido, titulo=titulo_defecto, pagina="", hashtags="")
        session.add(nueva_ficha)
        session.commit()
        id_nueva_ficha = nueva_ficha.id
        session.close()
        
        self.cargar_fichas_de_fuente()
        for i in range(self.lista_fichas.count()):
            item = self.lista_fichas.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == id_nueva_ficha:
                self.lista_fichas.setCurrentItem(item)
                self.mostrar_contenido_ficha(item)
                self.in_titulo.setFocus() 
                break

    def mostrar_menu_hashtags(self):
        menu = QMenu(self)
        session = Session()
        fichas = session.query(Ficha.hashtags).filter(Ficha.hashtags != "").all()
        session.close()
        
        tags_unicos = set()
        for f in fichas:
            if f.hashtags:
                tags_unicos.update([t.strip() for t in f.hashtags.split() if t.strip()])
                
        if not tags_unicos:
            accion = menu.addAction("No hay hashtags registrados")
            accion.setEnabled(False)
        else:
            for tag in sorted(tags_unicos):
                accion = menu.addAction(tag)
                accion.triggered.connect(lambda checked, t=tag: self.agregar_hashtag_a_input(t))
                
        menu.exec(self.btn_hashtags.mapToGlobal(self.btn_hashtags.rect().bottomLeft()))

    def agregar_hashtag_a_input(self, tag):
        texto_actual = self.in_hashtags.text().strip()
        if texto_actual:
            if tag not in texto_actual.split():
                self.in_hashtags.setText(texto_actual + " " + tag + " ")
        else:
            self.in_hashtags.setText(tag + " ")
        self.in_hashtags.setFocus()

    def cargar_fichas_de_fuente(self):
        self.lista_fichas.clear()
        self.limpiar_formulario()
        fuente_id = self.combo_fuentes.currentData()
        if not fuente_id: return
        
        session = Session()
        fichas = session.query(Ficha).filter(Ficha.fuente_id == fuente_id).all()
        for ficha in fichas:
            display_text = ficha.titulo if ficha.titulo else ficha.contenido_atomico[:40].replace('\n', ' ') + "..."
            if ficha.pagina: display_text = f"[Pág. {ficha.pagina}] {display_text}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, ficha.id)
            self.lista_fichas.addItem(item)
        session.close()

    def mostrar_contenido_ficha(self, item):
        ficha_id = item.data(Qt.ItemDataRole.UserRole)
        session = Session()
        ficha = session.query(Ficha).filter(Ficha.id == ficha_id).first()
        if ficha:
            self.in_titulo.setText(ficha.titulo or "")
            self.in_pagina.setText(ficha.pagina or "")
            self.in_hashtags.setText(ficha.hashtags or "")
            self.area_edicion_ficha.setPlainText(ficha.contenido_atomico)
        session.close()

    def guardar_edicion_ficha(self):
        item_seleccionado = self.lista_fichas.currentItem()
        if not item_seleccionado: return
        
        ficha_id = item_seleccionado.data(Qt.ItemDataRole.UserRole)
        session = Session()
        ficha = session.query(Ficha).filter(Ficha.id == ficha_id).first()
        if ficha:
            ficha.titulo = self.in_titulo.text()
            ficha.pagina = self.in_pagina.text()
            ficha.hashtags = self.in_hashtags.text()
            ficha.contenido_atomico = self.area_edicion_ficha.toPlainText()
            session.commit()
        session.close()
        
        self.actualizar_memoria_hashtags() # Refresca las opciones del autocompletador
        self.cargar_fichas_de_fuente() 

    def eliminar_ficha(self):
        item_seleccionado = self.lista_fichas.currentItem()
        if not item_seleccionado: return
        ficha_id = item_seleccionado.data(Qt.ItemDataRole.UserRole)
        respuesta = QMessageBox.question(self, "Confirmar", "¿Eliminar esta ficha?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if respuesta == QMessageBox.StandardButton.Yes:
            session = Session()
            ficha = session.query(Ficha).filter(Ficha.id == ficha_id).first()
            if ficha:
                session.delete(ficha)
                session.commit()
            session.close()
            self.actualizar_memoria_hashtags()
            self.cargar_fichas_de_fuente()
            self.limpiar_formulario()

    def limpiar_formulario(self):
        self.in_titulo.clear()
        self.in_pagina.clear()
        self.in_hashtags.clear()
        self.area_edicion_ficha.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = ModuloNotasReferencia()
    ventana.show()
    sys.exit(app.exec())
