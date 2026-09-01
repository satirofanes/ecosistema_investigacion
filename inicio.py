import sys
import os
import subprocess
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QPushButton, QLabel, QMessageBox, QDialog, QTextEdit)
from PyQt6.QtCore import Qt

class VentanaInformacion(QDialog):
    """Plantilla reutilizable para las ventanas de Ayuda, FAQ y Contacto"""
    def __init__(self, titulo, contenido_html, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e293b;
            }
            QTextEdit {
                background-color: transparent;
                color: #f8fafc;
                font-size: 14px;
                border: none;
            }
        """)
        
        layout = QVBoxLayout(self)
        visor_texto = QTextEdit()
        visor_texto.setReadOnly(True)
        visor_texto.setHtml(contenido_html)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; color: white; 
                padding: 8px; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        btn_cerrar.clicked.connect(self.close)
        
        layout.addWidget(visor_texto)
        layout.addWidget(btn_cerrar)

class LanzadorEcosistema(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ecosistema de Investigación")
        self.resize(800, 550)
        
        # Asignar un ID para aplicar el fondo a la ventana principal sin afectar a los hijos
        self.setObjectName("VentanaPrincipal")
        self.setStyleSheet("""
            #VentanaPrincipal {
                background-color: #0f172a;
                border-image: url('fondo.jpg') 0 0 0 0 stretch stretch;
            }
            QLabel { color: #f8fafc; }
        """)
        
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(40, 40, 40, 20)
        layout_principal.setSpacing(20)
        
        # --- ENCABEZADO ---
        lbl_titulo = QLabel("Panel de Control de Investigación")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_titulo.setStyleSheet("font-size: 28px; font-weight: bold; text-shadow: 2px 2px 4px #000000;")
        
        lbl_subtitulo = QLabel("Selecciona un módulo para iniciar tu sesión de trabajo")
        lbl_subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_subtitulo.setStyleSheet("font-size: 15px; color: #94a3b8; margin-bottom: 10px;")
        
        layout_principal.addWidget(lbl_titulo)
        layout_principal.addWidget(lbl_subtitulo)
        
        # --- GRID DE MÓDULOS ---
        grid = QGridLayout()
        grid.setSpacing(15)
        
        modulos = [
            ("Módulo 1\nGestión de Fuentes", "rgba(52, 73, 94, 0.9)", "modulo_fuentes.py"),
            ("Módulo 2\nFichas y Extracción", "rgba(22, 160, 133, 0.9)", "modulo_fichas.py"),
            ("Módulo 3\nLienzo Mental", "rgba(41, 128, 185, 0.9)", "modulo_lienzo.py"),
            ("Módulo 4\nDelineados y Word", "rgba(142, 68, 173, 0.9)", "modulo_composicion.py"),
        ]
        
        fila, col = 0, 0
        for titulo, color, archivo in modulos:
            btn = self.crear_boton_modulo(titulo, color, archivo)
            grid.addWidget(btn, fila, col)
            col += 1
            if col > 1:
                col = 0
                fila += 1
                
        btn_mod5 = self.crear_boton_modulo("Módulo 5\nGestión de Proyectos y Proyección Académica", "rgba(39, 174, 96, 0.9)", "modulo_gestion.py")
        grid.addWidget(btn_mod5, 2, 0, 1, 2)
        
        layout_principal.addLayout(grid)
        layout_principal.addStretch()
        
        # --- BARRA INFERIOR (INFORMACIÓN) ---
        barra_info = QHBoxLayout()
        
        btn_ayuda = self.crear_boton_info("❔ Ayuda", self.mostrar_ayuda)
        btn_faq = self.crear_boton_info("💬 Preguntas Frecuentes", self.mostrar_faq)
        btn_acerca = self.crear_boton_info("ℹ️ Acerca de y Contacto", self.mostrar_acerca)
        
        barra_info.addStretch()
        barra_info.addWidget(btn_ayuda)
        barra_info.addWidget(btn_faq)
        barra_info.addWidget(btn_acerca)
        barra_info.addStretch()
        
        layout_principal.addLayout(barra_info)

    def crear_boton_modulo(self, texto, color, archivo):
        btn = QPushButton(texto)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white; font-size: 16px; font-weight: bold;
                border-radius: 12px; padding: 25px;
                border: 1px solid rgba(255,255,255,0.2);
            }}
            QPushButton:hover {{
                background-color: #cbd5e1;
                color: #0f172a;
                border: 2px solid white;
            }}
        """)
        btn.clicked.connect(lambda: self.ejecutar_modulo(archivo))
        return btn

    def crear_boton_info(self, texto, funcion):
        btn = QPushButton(texto)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8; font-size: 13px; font-weight: bold;
                padding: 5px 15px; border-radius: 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
        """)
        btn.clicked.connect(funcion)
        return btn

    # --- RUTINAS DE EJECUCIÓN E INTERFACES FLOTANTES ---
    def ejecutar_modulo(self, nombre_archivo):
        if os.path.exists(nombre_archivo):
            try:
                subprocess.Popen([sys.executable, nombre_archivo])
            except Exception as e:
                QMessageBox.critical(self, "Error de Ejecución", f"No se pudo iniciar el módulo.\nDetalle: {str(e)}")
        else:
            QMessageBox.warning(self, "Módulo no encontrado", f"No se encontró el archivo '{nombre_archivo}'.")

    def mostrar_ayuda(self):
        html = """
        <h2>Guía de Uso Rápido</h2>
        <p>Este ecosistema está diseñado para acompañarte desde la lectura hasta la publicación.</p>
        <ul>
            <li><b>Módulo 1:</b> Registra tus libros y PDFs.</li>
            <li><b>Módulo 2:</b> Extrae citas textuales y parafraseos.</li>
            <li><b>Módulo 3:</b> Organiza tus ideas libremente en un lienzo infinito.</li>
            <li><b>Módulo 4:</b> Anida tus notas y expórtalas a Microsoft Word.</li>
            <li><b>Módulo 5:</b> Gestiona tus fechas de entrega y borrador final.</li>
        </ul>
        """
        dialogo = VentanaInformacion("Ayuda General", html, self)
        dialogo.exec()

    def mostrar_faq(self):
        html = """
        <h2>Preguntas Frecuentes</h2>
        <p><b>¿Dónde se guarda mi información?</b><br>
        Toda la información se almacena localmente en el archivo <i>investigacion_productiva.db</i>. No necesitas internet.</p>
        <p><b>¿Puedo hacer un respaldo?</b><br>
        Simplemente copia el archivo .db y llévalo a otra computadora con los scripts instalados.</p>
        <p><b>¿Qué hago si falla la exportación a Word?</b><br>
        Asegúrate de no tener el archivo .docx de destino abierto al momento de exportar.</p>
        """
        dialogo = VentanaInformacion("Preguntas Frecuentes", html, self)
        dialogo.exec()

    def mostrar_acerca(self):
        html = """
        <h2>Acerca del Ecosistema</h2>
        <p><b>Versión:</b> 1.0.0</p>
        <p><b>Licencia:</b> Uso personal y académico</p>
        <br>
        <p>Desarrollado como una solución integral para estructurar el caos creativo de la investigación antropológica y académica.</p>
        <p><b>Contacto y Soporte:</b></p>
        <p>tu-correo@archivodeantropologia.com<br>
        www.archivodeantropologia.com</p>
        """
        dialogo = VentanaInformacion("Acerca de y Contacto", html, self)
        dialogo.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = LanzadorEcosistema()
    ventana.show()
    sys.exit(app.exec())
