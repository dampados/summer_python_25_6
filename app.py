import sys
import pandas
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidget,
                             QTableWidgetItem, QPushButton,
                             QLineEdit, QVBoxLayout, QWidget, QMenu, QLabel,
                             QHBoxLayout, QTableView)
from PyQt6.QtCore import (Qt, QTimer, pyqtSignal, QThread, QObject, 
                          QRunnable, QThreadPool, QAbstractTableModel)
from PyQt6.QtGui import QAction, QMovie  # переход к pyqt6

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0%);")
        
        layout = QVBoxLayout(self)
        self.spinner = QLabel(self)
        self.movie = QMovie("media/loading2.gif")
        self.spinner.setMovie(self.movie)
        layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        
    def showEvent(self, a0):
        self.movie.start()
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(0, 0, parent.width(), parent.height())
        
    def hideEvent(self, a0):
        self.movie.stop()

class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

class Task(QRunnable):
    def __init__(self, func):
        super().__init__()
        self.func = func
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.func()
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))

def push_db_task(self, action, **kwargs): # жёсткий спавнинг конкретного таска, неблокирует!
    self.set_loading(True)
    task = Task(lambda: self.db_io_selector(action, **kwargs))
    task.signals.finished.connect(self.on_data_fetched) # -> с сигналом передаёмпейлоад в вызываемую функцию
    task.signals.error.connect(self.on_error)
    self.threadpool.start(task)

def db_io_selector(self, action, **kwargs):
    if action == 'fetchall':
        return db.get_all_posts()
    if action == 'fetchsome':
        return db.get_all_posts_by_field(kwargs["field"], kwargs["value"])
    if action == 'add_a_post':
        return db.add_a_post()
    if action == 'delete_selected_posts':
        return db.delete_posts(kwargs["post_ids"])
    if action == 'update':  
        return db.set_update_post(kwargs["post_id"], kwargs["column"], kwargs["value"])
    if action == 'init_db':
        db.init_db()
        return db.get_all_posts()

    raise ValueError(f"Неопознано!!! {action}")

class ViewModel_graphs(QObject):
    sgnl_data_loaded = pyqtSignal(pandas.DataFrame) # СИГНАЛ только по сигнулу
    sgnl_loading_state_changed = pyqtSignal(bool) # тип данных указываем!!!

    def __init__(self):
        super().__init__() # init наследуемого класса!
        self.data = pandas.DataFrame()
        self.is_loading = False

    # @property
    def get_data(self):
        return self.data
    
    # @property
    def get_is_loading(self):
        return self.is_loading

    def _set_loading(self, passed_loading_state):
        self.is_loading = passed_loading_state
        self.sgnl_loading_state_changed.emit(passed_loading_state) # эмиттим сигнал во View
    
    def _on_data_loaded(self, new_data):
        self.data = new_data
        self._set_loading(False) # ОБЯЗАТЕЛЬНО ВСЕГДА снимаем ввиджет
        self.sgnl_data_loaded.emit(new_data) # эмиттим сигнал во View

    def _on_error(self, error):
        print(f"Ошибка получения данных: {error}")
        
class View_graphs(QWidget):
    def __init__(self, view_model):
        super().__init__()
        self.view_model = view_model
        self.init_ui() # рендерим начальный ui
        # self.bind_signals() # коннектим сигналы к триггерам виджетов

    def init_ui(self):
        self.layout_root = QVBoxLayout(self)

        self.buttong_load_data = QPushButton("Загрузить данные")

        self.layout_root.addWidget(self.buttong_load_data)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.threadpool = QThreadPool()


        graphs_model = ViewModel_graphs()
        graphs_view = View_graphs(graphs_model)


        
        # add to layout everything


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())