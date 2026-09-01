import sys
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QGraphicsView, QGraphicsScene, 
                             QGraphicsProxyWidget, QTextEdit, QLineEdit, QFrame,
                             QSplitter, QListWidget, QLabel, QComboBox, QFileDialog, 
                             QMessageBox, QGraphicsPixmapItem, QGraphicsPathItem, QListWidgetItem, QMenu, QSpinBox)
from PyQt6.QtCore import Qt, QRectF, QPointF, QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QPainter, QImage, QPen, QColor, QPainterPath, QPixmap, QCursor
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
import copy

# --- CONFIGURACIÓN DE BD ---
Base = declarative_base()

class Ficha(Base):
    __tablename__ = 'fichas'
    id = Column(Integer, primary_key=True)
    fuente_id = Column(Integer)
    titulo = Column(String(150))          
    hashtags = Column(String(200))
    contenido_atomico = Column(Text, nullable=False)

class NotaPersonal(Base):
    __tablename__ = 'notas_personales'
    id = Column(Integer, primary_key=True)
    titulo = Column(String(150))
    desarrollo = Column(Text)
    pos_x = Column(Integer, default=0)
    pos_y = Column(Integer, default=0)
    hashtags = Column(String(200), default="")
    color_fondo = Column(String(20), default="#fef08a")

class LienzoEstado(Base):
    __tablename__ = 'lienzo_estado'
    id = Column(Integer, primary_key=True)
    datos_json = Column(Text, default="{}")

engine = create_engine('sqlite:///investigacion_productiva.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

MAPA_COLORES = {
    "🟡 Amarillo": "#fef08a", "🟢 Verde": "#bbf7d0", "🔵 Azul": "#bfdbfe",
    "🟣 Morado": "#e9d5ff", "🟠 Naranja": "#fed7aa", "⬜ Blanco": "#ffffff",
    "🔲 Transparente": "transparent"
}

portapapeles_nodos = []

# --- ELEMENTOS GRÁFICOS ---
class Conector(QGraphicsPathItem):
    def __init__(self, nodo_origen, nodo_destino):
        super().__init__()
        self.origen = nodo_origen
        self.destino = nodo_destino
        self.setPen(QPen(QColor("#94a3b8"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.setZValue(-1)
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        self.actualizar_posicion()

    def actualizar_posicion(self):
        path = QPainterPath()
        p1 = self.origen.sceneBoundingRect().center()
        p2 = self.destino.sceneBoundingRect().center()
        path.moveTo(p1)
        path.cubicTo(p1.x() + 50, p1.y(), p2.x() - 50, p2.y(), p2.x(), p2.y())
        self.setPath(path)

class ImagenRedimensionable(QGraphicsPixmapItem):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.setFlags(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable | QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable)
        self.resizing = False
        self.setAcceptHoverEvents(True)

    def hoverMoveEvent(self, event):
        rect = self.boundingRect()
        if event.pos().x() >= rect.width() - 20 and event.pos().y() >= rect.height() - 20:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        rect = self.boundingRect()
        if event.pos().x() >= rect.width() - 20 and event.pos().y() >= rect.height() - 20:
            self.resizing = True
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            nuevo_ancho = max(50, event.pos().x())
            factor = nuevo_ancho / self.pixmap().width()
            self.setScale(factor)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resizing = False
        super().mouseReleaseEvent(event)

class NodoNota(QGraphicsProxyWidget):
    def __init__(self, nota_id, titulo, contenido, hashtags, color, x, y, scene_manager):
        super().__init__()
        self.nota_id = nota_id
        self.scene_manager = scene_manager
        self.enlaces = []
        
        self.frame = QFrame()
        self.color_actual = color if color in MAPA_COLORES.values() else "#fef08a"
        
        self.frame.resize(320, 260)
        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        layout_top = QHBoxLayout()
        self.lbl_drag = QLabel("🖐️")
        self.lbl_drag.setStyleSheet("background: transparent; border: none;")
        
        self.in_titulo = QLineEdit(titulo)
        self.in_titulo.setPlaceholderText("Título...")
        
        self.combo_color = QComboBox()
        self.combo_color.addItems(MAPA_COLORES.keys())
        self.seleccionar_color_combo(self.color_actual)
        self.combo_color.currentIndexChanged.connect(self.cambiar_color_manual)
        
        layout_top.addWidget(self.lbl_drag)
        layout_top.addWidget(self.in_titulo, 1)
        layout_top.addWidget(self.combo_color)
        
        self.in_hashtags = QLineEdit(hashtags)
        self.in_hashtags.setPlaceholderText("#etiqueta")
        
        self.in_contenido = QTextEdit(contenido)
        self.in_contenido.setPlaceholderText("Desarrollo de la idea...")
        
        layout.addLayout(layout_top)
        layout.addWidget(self.in_hashtags)
        layout.addWidget(self.in_contenido, 1)
        
        self.actualizar_estilo()
        
        self.in_titulo.editingFinished.connect(self.guardar_cambios)
        self.in_hashtags.editingFinished.connect(self.guardar_cambios)
        
        self.setWidget(self.frame)
        self.setPos(x, y)
        self.setFlag(QGraphicsProxyWidget.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsProxyWidget.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.arrastrando = False

    def seleccionar_color_combo(self, hex_color):
        for texto, valor in MAPA_COLORES.items():
            if valor == hex_color:
                self.combo_color.setCurrentText(texto)
                return

    def cambiar_color_manual(self):
        seleccion = self.combo_color.currentText()
        self.color_actual = MAPA_COLORES.get(seleccion, "#fef08a")
        self.actualizar_estilo(self.isSelected())
        self.guardar_cambios()

    def actualizar_estilo(self, selected=False):
        borde = "3px dashed #3b82f6" if selected else ("none" if self.color_actual == "transparent" else "1px solid #cbd5e1")
        color_texto = "#e0f2fe" if self.color_actual == "transparent" else "#0f172a"
        fondo_inputs = "rgba(255,255,255,0.05)" if self.color_actual == "transparent" else "rgba(255,255,255,0.4)"
        bg_lbl = "rgba(0,0,0,0.2)" if self.color_actual == "transparent" else "rgba(0,0,0,0.1)"

        self.frame.setStyleSheet(f"""
            QFrame {{ background-color: {self.color_actual}; border: {borde}; border-radius: 8px; }}
            QLineEdit {{ background: {fondo_inputs}; border: none; font-weight: bold; font-size: 13px; color: {color_texto}; }}
            QTextEdit {{ background: transparent; border: none; font-size: 14px; color: {color_texto}; }}
            QLabel {{ background: {bg_lbl}; border-radius: 4px; padding: 2px; color: {color_texto}; }}
        """)

    def guardar_cambios(self):
        session = Session()
        nota = session.query(NotaPersonal).filter(NotaPersonal.id == self.nota_id).first()
        if nota:
            nota.titulo = self.in_titulo.text()
            nota.hashtags = self.in_hashtags.text()
            nota.desarrollo = self.in_contenido.toHtml()
            nota.color_fondo = self.color_actual
            nota.pos_x = int(self.pos().x())
            nota.pos_y = int(self.pos().y())
            session.commit()
        session.close()
        self.scene_manager.reconstruir_menu_hashtags()
        self.scene_manager.guardar_en_historial()

    def itemChange(self, change, value):
        if change == QGraphicsProxyWidget.GraphicsItemChange.ItemSelectedHasChanged:
            self.actualizar_estilo(selected=value)
        if change == QGraphicsProxyWidget.GraphicsItemChange.ItemPositionHasChanged:
            for enlace in self.enlaces: enlace.actualizar_posicion()
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if self.scene_manager.modo_enlace:
            self.scene_manager.registrar_clic_enlace(self)
            event.accept()
            return
        
        pos_local = event.pos()
        if pos_local.y() < 40 and pos_local.x() < 40: 
            self.arrastrando = True
            self.scene_manager.visor.setDragMode(QGraphicsView.DragMode.NoDrag)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.arrastrando:
            nuevo_pos = self.mapToScene(event.pos()) - QPointF(20, 20)
            self.setPos(nuevo_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.arrastrando:
            self.arrastrando = False
            self.scene_manager.visor.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.guardar_cambios()
            self.scene_manager.actualizar_minimapa() 
            event.accept()
        else:
            super().mouseReleaseEvent(event)
            self.scene_manager.actualizar_minimapa() 

# --- VISOR PRINCIPAL ---
class VisorLienzo(QGraphicsView):
    def __init__(self, scene, scene_manager):
        super().__init__(scene)
        self.scene_manager = scene_manager
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.factor_zoom = 1.0
        self.panning = False
        self.dibujando = False
        self.trazo_actual = None

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            zoom = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.factor_zoom *= zoom
            if 0.2 <= self.factor_zoom <= 5.0: self.scale(zoom, zoom)
        else:
            super().wheelEvent(event)
            
    def keyPressEvent(self, event):
        # 1. Bloqueo para widgets fuera del lienzo (ej. buscador superior)
        focus = QApplication.focusWidget()
        if isinstance(focus, (QLineEdit, QTextEdit, QSpinBox)):
            super().keyPressEvent(event)
            return

        # 2. Bloqueo preciso para cuando se escribe dentro de las notas del lienzo
        item_foco = self.scene().focusItem()
        if hasattr(item_foco, 'in_titulo'): # Verifica que sea un NodoNota
            if item_foco.in_titulo.hasFocus() or item_foco.in_hashtags.hasFocus() or item_foco.in_contenido.hasFocus():
                super().keyPressEvent(event)
                return

        # 3. Ejecución normal de atajos
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.panning = True
        elif event.key() == Qt.Key.Key_D and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.scene_manager.duplicar_seleccion()
        elif event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.scene_manager.copiar_seleccion()
        elif event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.scene_manager.pegar_portapapeles(self.mapToScene(self.mapFromGlobal(QCursor.pos())))
        elif event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.scene_manager.deshacer()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.scene_manager.eliminar_seleccion()
        
        elif not event.modifiers():
            if event.key() == Qt.Key.Key_N:
                self.scene_manager.crear_nota_vacia()
            elif event.key() == Qt.Key.Key_T:
                self.scene_manager.crear_texto_libre()
            elif event.key() == Qt.Key.Key_L:
                self.scene_manager.btn_dibujo.setChecked(not self.scene_manager.btn_dibujo.isChecked())
                self.scene_manager.toggle_dibujo()
            elif event.key() == Qt.Key.Key_E:
                self.scene_manager.btn_enlace.setChecked(not self.scene_manager.btn_enlace.isChecked())
                self.scene_manager.toggle_enlace()
                
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.panning = False
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        if self.scene_manager.modo_dibujo and event.button() == Qt.MouseButton.LeftButton:
            self.dibujando = True
            grosor = self.scene_manager.spin_grosor.value()
            self.trazo_actual = QGraphicsPathItem()
            self.trazo_actual.setPen(QPen(QColor("#3b82f6"), grosor, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            path = QPainterPath(self.mapToScene(event.pos()))
            self.trazo_actual.setPath(path)
            self.scene().addItem(self.trazo_actual)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dibujando and self.trazo_actual:
            path = self.trazo_actual.path()
            path.lineTo(self.mapToScene(event.pos()))
            self.trazo_actual.setPath(path)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dibujando:
            self.dibujando = False
            if self.trazo_actual:
                self.trazo_actual.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
            self.trazo_actual = None
            self.scene_manager.actualizar_minimapa()
            self.scene_manager.guardar_en_historial()
        else:
            super().mouseReleaseEvent(event)

# --- MÓDULO VISUAL PRINCIPAL ---
class VisorMinimapa(QGraphicsView):
    def __init__(self, visor_principal):
        super().__init__()
        self.visor_principal = visor_principal
        self.setInteractive(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Traduce el clic en el minimapa a coordenadas de la escena global
            punto_escena = self.mapToScene(event.pos())
            # Centra el visor principal en esa coordenada exacta
            self.visor_principal.centerOn(punto_escena)
        super().mousePressEvent(event)

class ModuloLienzoMental(QWidget):
    def actualizar_minimapa(self):
        self.minimapa.fitInView(self.escena.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Módulo 3: Desarrollo de Pensamiento Propio")
        self.resize(1300, 750)
        self.modo_enlace = False
        self.modo_dibujo = False
        self.nodo_origen_enlace = None
        self.undo_stack = []
        self.is_undoing = False
        
        layout_principal = QVBoxLayout(self)
        
        # --- BARRA SUPERIOR ---
        layout_controles = QHBoxLayout()
        self.btn_guardar_json = QPushButton("💾 Guardar Lienzo")
        self.btn_guardar_json.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_guardar_json.clicked.connect(self.guardar_estado_json)
        
        self.btn_nueva = QPushButton("➕ Nota (N)")
        self.btn_nueva.clicked.connect(self.crear_nota_vacia)
        
        self.btn_texto = QPushButton("🔤 Texto (T)")
        self.btn_texto.clicked.connect(self.crear_texto_libre)

        self.btn_alinear = QPushButton("📏 Alinear")
        menu_alinear = QMenu(self)
        menu_alinear.addAction("Alinear Arriba", lambda: self.alinear_seleccion('arriba'))
        menu_alinear.addAction("Alinear Abajo", lambda: self.alinear_seleccion('abajo'))
        menu_alinear.addAction("Alinear Izquierda", lambda: self.alinear_seleccion('izquierda'))
        menu_alinear.addAction("Alinear Derecha", lambda: self.alinear_seleccion('derecha'))
        self.btn_alinear.setMenu(menu_alinear)
        
        self.btn_enlace = QPushButton("🔗 Enlace (E)")
        self.btn_enlace.setCheckable(True)
        self.btn_enlace.clicked.connect(self.toggle_enlace)
        
        self.btn_dibujo = QPushButton("🖍️ Lápiz (L)")
        self.btn_dibujo.setCheckable(True)
        self.btn_dibujo.clicked.connect(self.toggle_dibujo)
        
        lbl_grosor = QLabel("Grosor:")
        self.spin_grosor = QSpinBox()
        self.spin_grosor.setRange(1, 20)
        self.spin_grosor.setValue(4)
        
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("🔍 Buscar...")
        self.buscador.textChanged.connect(self.filtrar_busqueda)
        
        self.combo_tags = QComboBox()
        self.combo_tags.addItem("🏷️ Todos los Hashtags")
        self.combo_tags.currentTextChanged.connect(self.actualizar_filtros)
        
        self.btn_png = QPushButton("📸 Exportar")
        self.btn_png.clicked.connect(self.exportar_png)
        
        layout_controles.addWidget(self.btn_guardar_json)
        layout_controles.addWidget(self.btn_nueva)
        layout_controles.addWidget(self.btn_texto)
        layout_controles.addWidget(self.btn_alinear)
        layout_controles.addWidget(self.btn_enlace)
        layout_controles.addWidget(self.btn_dibujo)
        layout_controles.addWidget(lbl_grosor)
        layout_controles.addWidget(self.spin_grosor)
        layout_controles.addWidget(self.buscador)
        layout_controles.addWidget(self.combo_tags)
        layout_controles.addStretch()
        layout_controles.addWidget(self.btn_png)
        
        # --- ÁREA CENTRAL ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        panel_izq = QWidget()
        layout_izq = QVBoxLayout(panel_izq)
        layout_izq.setContentsMargins(0,0,5,0)
        
        lbl_mini = QLabel("<b>Minimapa</b>")
        lbl_mini.setStyleSheet("color: white;")
        layout_izq.addWidget(lbl_mini)
        
        # Inicializamos el visor principal ANTES del minimapa
        self.escena = QGraphicsScene()
        self.escena.setSceneRect(-5000, -5000, 10000, 10000)
        self.visor = VisorLienzo(self.escena, self)
        self.visor.setStyleSheet("background-color: #1e293b;")

        # Ahora inicializamos el minimapa pasándole el visor principal
        self.minimapa = VisorMinimapa(self.visor)
        self.minimapa.setFixedHeight(150)
        self.minimapa.setStyleSheet("background: #0f172a; border: 1px solid #334155;")
        layout_izq.addWidget(self.minimapa)
        
        lbl_fichas = QLabel("<b>Fichas Guardadas</b>")
        lbl_fichas.setStyleSheet("color: white;")
        layout_izq.addWidget(lbl_fichas)
        
        self.lista_fichas = QListWidget()
        self.lista_fichas.itemDoubleClicked.connect(self.insertar_desde_ficha)
        layout_izq.addWidget(self.lista_fichas)
        panel_izq.setStyleSheet("background-color: #1e293b;") 
        
        self.minimapa.setScene(self.escena)
        
        splitter.addWidget(panel_izq)
        splitter.addWidget(self.visor)
        splitter.setSizes([250, 1050])
        
        layout_principal.addLayout(layout_controles)
        layout_principal.addWidget(splitter)
        
        self.cargar_datos()

    # --- SISTEMA DE HISTORIAL Y SERIALIZACIÓN ---
    def capturar_estado(self):
        """Serializa todos los objetos de la escena en JSON[cite: 2]"""
        estado = {"notas": [], "trazos": [], "enlaces": [], "imagenes": []}
        for item in self.escena.items():
            if isinstance(item, NodoNota):
                estado["notas"].append({
                    "id": item.nota_id, "titulo": item.in_titulo.text(),
                    "contenido": item.in_contenido.toHtml(), "hashtags": item.in_hashtags.text(),
                    "color": item.color_actual, "x": item.pos().x(), "y": item.pos().y()
                })
            elif isinstance(item, Conector):
                estado["enlaces"].append({
                    "origen": item.origen.nota_id, "destino": item.destino.nota_id
                })
            elif isinstance(item, QGraphicsPathItem) and not isinstance(item, Conector):
                path = item.path()
                puntos = [{"tipo": path.elementAt(i).type.value, "x": path.elementAt(i).x, "y": path.elementAt(i).y} for i in range(path.elementCount())]
                estado["trazos"].append({
                    "puntos": puntos, "grosor": item.pen().width(), "color": item.pen().color().name()
                })
            elif isinstance(item, ImagenRedimensionable):
                ba = QByteArray()
                buffer = QBuffer(ba)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                item.pixmap().toImage().save(buffer, "PNG")
                estado["imagenes"].append({
                    "x": item.pos().x(), "y": item.pos().y(), "escala": item.scale(),
                    "data": ba.toBase64().data().decode()
                })
        return json.dumps(estado)

    def guardar_en_historial(self):
        """Almacena el estado actual limitando la memoria a 20 cambios[cite: 2]"""
        if self.is_undoing: return
        if len(self.undo_stack) > 20: self.undo_stack.pop(0)
        self.undo_stack.append(self.capturar_estado())

    def deshacer(self):
        if len(self.undo_stack) > 1:
            self.is_undoing = True
            self.undo_stack.pop() # Descarta el estado actual fallido
            estado_anterior = self.undo_stack[-1]
            self.restaurar_estado(estado_anterior)
            self.is_undoing = False

    def restaurar_estado(self, json_str):
        """Wipea el canvas y la BD, e inyecta el snapshot recuperado[cite: 2]"""
        datos = json.loads(json_str)
        session = Session()
        
        # 1. Limpieza y Recuperación de BD
        session.query(NotaPersonal).delete()
        self.escena.clear()
        diccionario_nodos = {}
        
        for n in datos.get("notas", []):
            nota = NotaPersonal(id=n["id"], titulo=n["titulo"], desarrollo=n["contenido"], hashtags=n["hashtags"], color_fondo=n["color"], pos_x=n["x"], pos_y=n["y"])
            session.add(nota)
            nodo = NodoNota(nota.id, nota.titulo or "", nota.desarrollo or "", nota.hashtags or "", nota.color_fondo, nota.pos_x, nota.pos_y, self)
            self.escena.addItem(nodo)
            diccionario_nodos[nota.id] = nodo
            
        session.commit()
        session.close()

        # 2. Restauración de Trazos y Enlaces
        for trazo_data in datos.get("trazos", []):
            path = QPainterPath()
            for pt in trazo_data["puntos"]:
                if pt["tipo"] == 0: path.moveTo(pt["x"], pt["y"])
                elif pt["tipo"] == 1: path.lineTo(pt["x"], pt["y"])
            trazo = QGraphicsPathItem(path)
            trazo.setPen(QPen(QColor(trazo_data["color"]), trazo_data["grosor"], Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            trazo.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
            self.escena.addItem(trazo)

        for enlace_data in datos.get("enlaces", []):
            origen = diccionario_nodos.get(enlace_data["origen"])
            destino = diccionario_nodos.get(enlace_data["destino"])
            if origen and destino:
                flecha = Conector(origen, destino)
                self.escena.addItem(flecha)
                origen.enlaces.append(flecha)
                destino.enlaces.append(flecha)
                
        # 3. Restauración de Imágenes Base64
        for img_data in datos.get("imagenes", []):
            ba = QByteArray.fromBase64(img_data["data"].encode())
            pixmap = QPixmap.fromImage(QImage.fromData(ba, "PNG"))
            pixmap_item = ImagenRedimensionable(pixmap)
            pixmap_item.setPos(img_data["x"], img_data["y"])
            pixmap_item.setScale(img_data["escala"])
            self.escena.addItem(pixmap_item)

        self.reconstruir_menu_hashtags()
        self.actualizar_minimapa()

    # --- FLUJO REGULAR DE APLICACIÓN ---
    def guardar_estado_json(self):
        """Guarda en BD el estado JSON del historial actual para sesiones futuras"""
        if not self.undo_stack: return
        session = Session()
        estado = session.query(LienzoEstado).first()
        if not estado:
            estado = LienzoEstado()
            session.add(estado)
        
        estado.datos_json = self.undo_stack[-1] # Toma el último snapshot generado
        session.commit()
        session.close()
        QMessageBox.information(self, "Guardado", "Lienzo (notas, imágenes y trazos) guardado correctamente.")

    def cargar_datos(self):
        self.escena.clear()
        session = Session()
        self.lista_fichas.clear()
        fichas = session.query(Ficha).all()
        for f in fichas:
            item = QListWidgetItem(f"{f.titulo or 'Sin Título'} - {f.contenido_atomico[:30]}...")
            item.setData(Qt.ItemDataRole.UserRole, f.id)
            self.lista_fichas.addItem(item)
            
        estado = session.query(LienzoEstado).first()
        if estado and estado.datos_json:
            self.restaurar_estado(estado.datos_json) # Usa la misma vía que Ctrl+Z
        else:
            notas = session.query(NotaPersonal).all()
            for nota in notas:
                nodo = NodoNota(nota.id, nota.titulo or "", nota.desarrollo or "", nota.hashtags or "", nota.color_fondo, nota.pos_x, nota.pos_y, self)
                self.escena.addItem(nodo)
            self.reconstruir_menu_hashtags()
            self.actualizar_minimapa()
            
        session.close()
        self.guardar_en_historial() # Snapshot inicial[cite: 2]

    def reconstruir_menu_hashtags(self):
        tag_actual = self.combo_tags.currentText()
        self.combo_tags.blockSignals(True)
        self.combo_tags.clear()
        self.combo_tags.addItem("🏷️ Todos los Hashtags")
        
        tags_unicos = set()
        for item in self.escena.items():
            if isinstance(item, NodoNota):
                for tag in item.in_hashtags.text().split(): tags_unicos.add(tag)
                    
        self.combo_tags.addItems(sorted(tags_unicos))
        if tag_actual in tags_unicos or tag_actual == "🏷️ Todos los Hashtags":
            self.combo_tags.setCurrentText(tag_actual)
        self.combo_tags.blockSignals(False)

    def alinear_seleccion(self, tipo):
        items = [i for i in self.escena.selectedItems() if isinstance(i, NodoNota)]
        if len(items) < 2: return
        
        if tipo == 'arriba': val = min(i.pos().y() for i in items)
        elif tipo == 'abajo': val = max(i.pos().y() for i in items)
        elif tipo == 'izquierda': val = min(i.pos().x() for i in items)
        elif tipo == 'derecha': val = max(i.pos().x() for i in items)
            
        for i in items:
            if tipo in ['arriba', 'abajo']: i.setPos(i.pos().x(), val)
            else: i.setPos(val, i.pos().y())
            i.guardar_cambios()
            for enlace in i.enlaces: enlace.actualizar_posicion()
        self.actualizar_minimapa()
        self.guardar_en_historial()

    def eliminar_seleccion(self):
        items = self.escena.selectedItems()
        if not items: return
        session = Session()
        for item in items:
            if isinstance(item, NodoNota):
                nota = session.query(NotaPersonal).filter(NotaPersonal.id == item.nota_id).first()
                if nota: session.delete(nota)
                for enlace in list(item.enlaces): 
                    if enlace in self.escena.items(): self.escena.removeItem(enlace)
                    if enlace in enlace.origen.enlaces: enlace.origen.enlaces.remove(enlace)
                    if enlace in enlace.destino.enlaces: enlace.destino.enlaces.remove(enlace)
                self.escena.removeItem(item)
            elif isinstance(item, Conector):
                if item in self.escena.items(): self.escena.removeItem(item)
                if item in item.origen.enlaces: item.origen.enlaces.remove(item)
                if item in item.destino.enlaces: item.destino.enlaces.remove(item)
            else:
                self.escena.removeItem(item)
        session.commit()
        session.close()
        self.reconstruir_menu_hashtags()
        self.actualizar_minimapa()
        self.guardar_en_historial()

    def crear_nota_vacia(self):
        centro = self.visor.mapToScene(self.visor.viewport().rect().center())
        self.inyectar_nota_bd("", "", "", "#fef08a", int(centro.x()), int(centro.y()))

    def crear_texto_libre(self):
        centro = self.visor.mapToScene(self.visor.viewport().rect().center())
        self.inyectar_nota_bd("Texto", "Escribe aquí...", "", "transparent", int(centro.x()), int(centro.y()))

    def insertar_desde_ficha(self, item):
        ficha_id = item.data(Qt.ItemDataRole.UserRole)
        session = Session()
        ficha = session.query(Ficha).filter(Ficha.id == ficha_id).first()
        if ficha:
            centro = self.visor.mapToScene(self.visor.viewport().rect().center())
            self.inyectar_nota_bd(ficha.titulo or "Cita", ficha.contenido_atomico, ficha.hashtags or "", "#fef08a", int(centro.x()), int(centro.y()))
        session.close()

    def inyectar_nota_bd(self, titulo, contenido, hashtags, color, x, y):
        session = Session()
        nueva = NotaPersonal(titulo=titulo, desarrollo=contenido, hashtags=hashtags, color_fondo=color, pos_x=x, pos_y=y)
        session.add(nueva)
        session.commit()
        nodo = NodoNota(nueva.id, titulo, contenido, hashtags, color, x, y, self)
        self.escena.addItem(nodo)
        session.close()
        self.reconstruir_menu_hashtags()
        self.actualizar_minimapa()
        self.guardar_en_historial()

    def copiar_seleccion(self):
        global portapapeles_nodos
        portapapeles_nodos = []
        for item in self.escena.selectedItems():
            if isinstance(item, NodoNota):
                portapapeles_nodos.append({
                    "t": item.in_titulo.text(), "c": item.in_contenido.toHtml(),
                    "h": item.in_hashtags.text(), "col": item.color_actual
                })

    def pegar_portapapeles(self, pos):
        portapapeles_os = QApplication.clipboard()
        if portapapeles_os.mimeData().hasImage():
            pixmap = portapapeles_os.pixmap()
            if not pixmap.isNull():
                pixmap_item = ImagenRedimensionable(pixmap)
                pixmap_item.setPos(pos)
                self.escena.addItem(pixmap_item)
                self.actualizar_minimapa()
                self.guardar_en_historial()
                return
                
        global portapapeles_nodos
        offset_x, offset_y = 0, 0
        for datos in portapapeles_nodos:
            self.inyectar_nota_bd(datos["t"]+" (Copia)", datos["c"], datos["h"], datos["col"], int(pos.x())+offset_x, int(pos.y())+offset_y)
            offset_x += 30; offset_y += 30

    def duplicar_seleccion(self):
        self.copiar_seleccion()
        centro = self.visor.mapToScene(self.visor.viewport().rect().center())
        self.pegar_portapapeles(centro)

    def toggle_enlace(self):
        self.modo_enlace = self.btn_enlace.isChecked()
        self.nodo_origen_enlace = None
        if self.modo_enlace:
            self.visor.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.visor.viewport().setCursor(Qt.CursorShape.CrossCursor)
            self.btn_dibujo.setChecked(False)
            self.modo_dibujo = False
        else:
            self.visor.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.visor.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        
    def registrar_clic_enlace(self, nodo):
        if not self.nodo_origen_enlace:
            self.nodo_origen_enlace = nodo
        else:
            if self.nodo_origen_enlace != nodo:
                flecha = Conector(self.nodo_origen_enlace, nodo)
                self.escena.addItem(flecha)
                self.nodo_origen_enlace.enlaces.append(flecha)
                nodo.enlaces.append(flecha)
            self.nodo_origen_enlace = None
            self.btn_enlace.setChecked(False)
            self.toggle_enlace()
            self.actualizar_minimapa()
            self.guardar_en_historial()

    def toggle_dibujo(self):
        self.modo_dibujo = self.btn_dibujo.isChecked()
        if self.modo_dibujo:
            self.visor.setDragMode(QGraphicsView.DragMode.NoDrag)
            pixmap = QPixmap(12, 12)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor("#3b82f6"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, 12, 12)
            painter.end()
            self.visor.viewport().setCursor(QCursor(pixmap, 6, 6))
            self.btn_enlace.setChecked(False)
            self.modo_enlace = False
        else:
            self.visor.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.visor.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def filtrar_busqueda(self, texto):
        texto = texto.lower()
        for item in self.escena.items():
            if isinstance(item, NodoNota):
                contenido = item.in_titulo.text().lower() + item.in_contenido.toPlainText().lower()
                item.setOpacity(1.0 if texto in contenido else 0.2)

    def actualizar_filtros(self):
        tag_seleccionado = self.combo_tags.currentText()
        if tag_seleccionado == "🏷️ Todos los Hashtags":
            for item in self.escena.items():
                if isinstance(item, NodoNota): item.setVisible(True)
        else:
            for item in self.escena.items():
                if isinstance(item, NodoNota):
                    item.setVisible(tag_seleccionado in item.in_hashtags.text().split())

    def exportar_png(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar Lienzo", "", "PNG (*.png)")
        if ruta:
            rect = self.escena.itemsBoundingRect() 
            rect.adjust(-50, -50, 50, 50)
            img = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
            img.fill(QColor("#1e293b")) 
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.escena.render(painter, target=QRectF(img.rect()), source=rect)
            painter.end()
            img.save(ruta)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = ModuloLienzoMental()
    ventana.show()
    sys.exit(app.exec())
