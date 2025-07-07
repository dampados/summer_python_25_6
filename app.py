# class ViewModel_graphs(QObject):
#     data_updated = pyqtSignal(object)  # Generic signal for all actions
#     error_occurred = pyqtSignal(str)

#     def dispatch(self, action, payload=None):
#         """Centralized async action handler."""
#         if action == Action.LOAD_CSV:
#             self.push_task(
#                 lambda: pd.read_csv(payload["file_path"]),
#                 on_success=lambda data: self._handle_action(Action.LOAD_CSV, data)
#             )
#         elif action == Action.LOAD_DB_POSTS:
#             self.push_task(
#                 lambda: self.db_io_selector("fetchall")),
#                 on_success=lambda data: self._handle_action(Action.LOAD_DB_POSTS, data)
#             )

#     def _handle_action(self, action, result):
#         """Process action results."""
#         if action == Action.LOAD_CSV:
#             self.data_updated.emit({"type": "graph_data", "data": result})
#         elif action == Action.LOAD_DB_POSTS:
#             self.data_updated.emit({"type": "posts_data", "data": result})

# # Usage:
# view_model.dispatch(Action.LOAD_CSV, {"file_path": "data.csv"})

# ПРАВИЛЬНЫЙ ПАТТЕРН НА РАСШИРЕНИЕ

import sys
import pandas
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidget,
                             QTableWidgetItem, QPushButton,
                             QLineEdit, QVBoxLayout, QWidget, QMenu, QLabel,
                             QHBoxLayout, QTableView)
from PyQt6.QtCore import (Qt, QTimer, pyqtSignal, QThread, QObject, 
                          QRunnable, QThreadPool, QAbstractTableModel, pyqtProperty)
from PyQt6.QtGui import QAction, QMovie  # переход к pyqt6

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import time

# GLOBALS
FILEPATH = "sample_data.csv"

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

class ViewModel_graphs(QObject):
    sgnl_data_changed = pyqtSignal(pandas.DataFrame) # СИГНАЛ только по сигнулу
    sgnl_loading_state_changed = pyqtSignal(bool) # тип данных указываем!!!
    sgnl_error = pyqtSignal(str)

    def __init__(self):
        super().__init__() # init наследуемого класса!
        self._data = pandas.DataFrame()
        self._is_loading = False                      
        self.threadpool = QThreadPool()

    @pyqtProperty(bool, notify=sgnl_loading_state_changed)
    def is_loading(self):
        return self._is_loading
    
    @is_loading.setter
    def is_loading(self, new_value):
        self._is_loading = new_value
        self.sgnl_loading_state_changed.emit(new_value)

    @pyqtProperty(bool, notify=sgnl_data_changed)
    def data(self):
        return self._data
    
    @data.setter
    def data(self, new_value):
        self._data = new_value
        self.sgnl_data_changed.emit(new_value)


    def task_load_data_from_csv(self):
        # self._set_loading(True)                                        # ОБЯЗАТЕЛЬНО ВСЕГДА локаем ввиджет
        self.is_loading = True                                           # ОБЯЗАТЕЛЬНО ВСЕГДА локаем ввиджет (ИДИОМАТИЧНО)
        task = Task(lambda: self.read_slowly_csv())
        task.signals.finished.connect(self._on_task_load_data_success) # -> реакции
        task.signals.error.connect(self._on_error)                     # -> реакции
        self.threadpool.start(task)

    def read_slowly_csv(self):
        time.sleep(5)
        return pandas.read_csv(FILEPATH)

    # def _set_loading(self, passed_loading_state):
    #     self.is_loading = passed_loading_state
    #     self.sgnl_loading_state_changed.emit(passed_loading_state) # эмиттим сигнал во View

    # реакции    
    def _on_task_load_data_success(self, payload):
        self.is_loading = False # ОБЯЗАТЕЛЬНО ВСЕГДА снимаем ввиджет
        self.data = payload

    def _on_error(self, error):
        print(f"Ошибка получения данных: {error}")
        
class View_graphs(QWidget):
    def __init__(self, view_model):
        super().__init__()
        self.view_model = view_model
        self.init_meta_widget_ui() # рендерим начальный ui
        self.bind_signals() # коннектим сигналы к триггерам виджетов

    def init_meta_widget_ui(self):

        self.layout_root = QVBoxLayout(self)

        self.buttong_load_data = QPushButton("Загрузить данные")

        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)


        self.layout_root.addWidget(self.buttong_load_data)
        self.layout_root.addWidget(self.canvas)

        self.graph_spinner = LoadingOverlay(self) # сложность...
        self.graph_spinner.hide()

    def bind_signals(self):
        self.buttong_load_data.clicked.connect(lambda: self.view_model.task_load_data_from_csv()) # НИКАКИХ ДАННЫХ ИЗ VIEW
        
        # РЕАКЦИИ НА СИГНАЛЫ ИЗ АБСТРАКЦИИ
        self.view_model.sgnl_data_changed.connect(self.reaction_update_view)
        self.view_model.sgnl_loading_state_changed.connect(self.reaction_update_spinner)

    def reaction_update_view(self, payload): # по факту реакция на сигнал, в payload разгрузит дату
        self.data = payload

        self.canvas.figure.clear() # всегда чистим переде действием

        ax = self.canvas.figure.add_subplot(111)
        self.data['Date'] = pandas.to_datetime(self.data['Date'])
        ax.plot(self.data['Date'], self.data['Value1'])

        # Set title and labels
        ax.set_title('Линейный график')
        ax.set_xlabel('Date')
        ax.set_ylabel('Value1')

        # Update the graph canvas
        self.canvas.draw()

    def reaction_update_spinner(self, is_loading):
        self.buttong_load_data.setEnabled(not is_loading)
        if is_loading:
            self.graph_spinner.show()  # Assuming you've added LoadingOverlay
        else:
            self.graph_spinner.hide()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.graphs_model = ViewModel_graphs()
        self.graphs_view = View_graphs(self.graphs_model)

        self.setCentralWidget(self.graphs_view)


        
        # add to layout everything


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())