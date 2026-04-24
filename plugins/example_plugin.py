"""Przykładowy plugin dodający przycisk w menu."""
def register(app):
    from PySide6.QtWidgets import QAction, QMessageBox
    action = QAction("Hello Plugin", app)
    action.triggered.connect(lambda: QMessageBox.information(app, "Plugin", "Hello z przykładowego pluginu!"))
    app.menuBar().addAction(action)
    print("Example plugin: akcja dodana do menu.")
