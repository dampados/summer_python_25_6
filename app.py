import sys
import pandas
from PyQt6.QtWidgets import (QApplication, QMainWindow,
                             QPushButton, QVBoxLayout, QWidget, 
                             QLabel, QComboBox, QHBoxLayout)
from PyQt6.QtCore import (Qt, pyqtSignal, QObject, 
                          QRunnable, QThreadPool, pyqtProperty)
from PyQt6.QtGui import QMovie  # переход к pyqt6

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import time

# GLOBALS
FILEPATH = "sample_data.csv"
DELAY = 1

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

class StatsData:
    def __init__(self, row_count=0, col_count=0, columns_stats={}):
        self.row_count = row_count
        self.col_count = col_count
        self.columns_stats = columns_stats

class ViewModel_graphs(QObject):
    sgnl_loading_state_changed = pyqtSignal(bool) # тип данных указываем!!!

    sgnl_data_changed = pyqtSignal(pandas.DataFrame) # СИГНАЛ только по сигнулу
    sgnl_error_data = pyqtSignal(str)

    sgnl_stats_changed = pyqtSignal(StatsData)
    sgnl_error_stats = pyqtSignal(str)

    def __init__(self):
        super().__init__() # init наследуемого класса!
        self._data = pandas.DataFrame()
        self._is_loading = False
        self._stats_data = StatsData()
        self.threadpool = QThreadPool()

    @pyqtProperty(StatsData, notify=sgnl_stats_changed)
    def stats_data(self):
        return self._stats_data
    
    @stats_data.setter
    def stats_data(self, new_value):
        self._stats_data = new_value
        self.sgnl_stats_changed.emit(new_value)

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

    # callable точка входа в загрузку данных
    def task_load_data_from_csv(self):
        # self._set_loading(True)                                        # ОБЯЗАТЕЛЬНО ВСЕГДА локаем ввиджет
        self.is_loading = True                                           # ОБЯЗАТЕЛЬНО ВСЕГДА локаем ввиджет (ИДИОМАТИЧНО)
        task = Task(lambda: self._read_slowly_csv())
        task.signals.finished.connect(self._on_task_load_data_success) # -> реакции
        task.signals.error.connect(self._on_any_error)                     # -> реакции
        self.threadpool.start(task)

    def _read_slowly_csv(self):
        time.sleep(DELAY)
        dataframe = pandas.read_csv(FILEPATH).copy() # наконец  столкнулся с одновременным доступом из разных тредов. питон пассит референсы, не копии. пока без мьютекса
        dataframe_for_parsing = dataframe
        dataframe_for_rendering = dataframe
        self._task_parse_data_from_csv(dataframe_for_parsing)
        return dataframe_for_rendering

    def _task_parse_data_from_csv(self, dataframe):
        task = Task(lambda: self._parse_data_from_csv(dataframe))
        task.signals.finished.connect(self._on_task_parse_data_success) # -> реакции
        task.signals.error.connect(self._on_any_error)                     # -> реакции
        self.threadpool.start(task)

    def _parse_data_from_csv(self, dataframe):
        row_count = dataframe.shape[0]
        col_count = dataframe.shape[1]
        column_stats = {}
        for col in dataframe.columns:
            column_stats[col] = (dataframe[col].min(), dataframe[col].max())
        new_stats_data = StatsData(row_count, col_count, column_stats)
        return new_stats_data

    # реакции (приватные, т.к. реакции меняют стейт) МЕНЯЕМ СТЕЙТ ТОЛЬКО ОТСЮДА ПО СИГНАЛУ+ПЕЙЛОАДУ
    def _on_task_load_data_success(self, payload):
        self.is_loading = False # ОБЯЗАТЕЛЬНО ВСЕГДА снимаем ввиджет
        self.data = payload

    def _on_task_parse_data_success(self, payload):
        self.stats_data = payload

    def _on_any_error(self, error):
        print(f"Сигнализация! : {error}")
        
class View_graphs(QWidget):
    def __init__(self, view_model):
        super().__init__()
        self.view_model = view_model
        self.init_meta_widget_ui() # рендерим начальный ui
        self.bind_signals() # коннектим сигналы к триггерам виджетов

    def init_meta_widget_ui(self):

        self.layout_root = QVBoxLayout(self)

        self.button_load_data = QPushButton("Загрузить данные")
        self.button_add_data = QPushButton("Добавить данные")
        self.button_add_data.setEnabled(False)

        self.label_statistics = QLabel("Статистика пуста")

        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)

        self.combo_type_chooser = QComboBox()
        self.combo_type_chooser.addItem("Линейный график")
        self.combo_type_chooser.addItem("Гистограмма")
        self.combo_type_chooser.addItem("Круговая диаграмма")
        self.combo_type_chooser.setEnabled(False)

        # vvv техничка vvv
        # добавляторы, порядок важен
        self.layout_upper_block = QHBoxLayout()
        self.layout_upper_block.addWidget(self.button_load_data)
        self.layout_upper_block.addWidget(self.button_add_data)
        self.layout_upper_block.addWidget(self.combo_type_chooser)

        self.layout_root.addLayout(self.layout_upper_block)
        # self.layout_root.addWidget(self.button_load_data)
        self.layout_root.addWidget(self.label_statistics)
        # self.layout_root.addWidget(self.combo_type_chooser)
        self.layout_root.addWidget(self.canvas)


        # прибиваем спиннер к уже собранному метавиджету СЕЛФ
        self.graph_spinner = LoadingOverlay(self) # сложность...
        self.graph_spinner.hide()

    def bind_signals(self):
        self.button_load_data.clicked.connect(lambda: self.view_model.task_load_data_from_csv()) # НИКАКИХ ДАННЫХ СУРСИМ ИЗ VIEW
        self.combo_type_chooser.currentTextChanged.connect(self.redraw_canvas) # ОБНОВЛЯЕМ ИЗ self.data!!!!
        
    # vvvvvvvvvvvvvv РЕАКЦИИ НА СИГНАЛЫ ИЗ АБСТРАКЦИИ vvvvvvvvvvvvvv
        self.view_model.sgnl_loading_state_changed.connect(self.reaction_update_lock_n_spinner)
        self.view_model.sgnl_stats_changed.connect(self.reaction_update_statistics_label)
        self.view_model.sgnl_data_changed.connect(self.reaction_update_canvas)

    def reaction_update_statistics_label(self, payload):
        text = f"Строк: {payload.row_count}\n" # просто перенос каретки, проще, хороший совет
        text += f"Колонок: {payload.col_count}\n\n"
        for col, (min_val, max_val) in payload.columns_stats.items():
            text += f"Столбец: {col} - МИН: {min_val}, МАКС: {max_val}\n"

        self.label_statistics.setText(text)

    def reaction_update_canvas(self, payload): # по факту реакция на сигнал, в payload разгрузит дату

        option = self.combo_type_chooser.currentText()
        self.data = payload # референс, не страшно. объявляется только тут, стоит проверку докинуть? #TODO проверка на несуществующий self.data

        print(self.data) # ска ведь пейлоад нормальный, чего тебе надо
        try:
            self.redraw_canvas(option)
        except Exception as e:
            print(e)

    # ^^^^^^^^^^^^^^ РЕАКЦИИ НА СИГНАЛЫ ИЗ АБСТРАКЦИИ ^^^^^^^^^^^^^^
   
    def redraw_canvas(self, option):
        self.canvas.figure.clear() # всегда чистим переде действием

        if option == "Линейный график":
            self.draw_linear(self.data)
        elif option == "Гистограмма":
            self.draw_hist(self.data)
        elif option == "Круговая диаграмма":
            self.draw_circle(self.data)
        else:
            print(option)

    def draw_linear(self, payload):
        print("Drawing plot")
        ax = self.canvas.figure.add_subplot(111)

        payload['Date'] = pandas.to_datetime(payload['Date'])
        ax.plot(payload['Date'], payload['Value1'])

        ax.set_title('Линейный график')
        ax.set_xlabel('Date')
        ax.set_ylabel('Value1')

        self.canvas.draw()

    def draw_hist(self, payload):
        print("Drawing plot")
        ax = self.canvas.figure.add_subplot(111)

        payload['Date'] = pandas.to_datetime(payload['Date'])
        ax.hist(payload['Value2'], bins=10)

        ax.set_title('Гистограмма')
        ax.set_xlabel('Value2')
        ax.set_ylabel('Частота')

        self.canvas.draw()

    def draw_circle(self, payload):
        print("Drawing plot")
        ax = self.canvas.figure.add_subplot(111)

        categories = payload['Category'].value_counts()
        ax.pie(categories, labels=categories.index, autopct='%1.1f%%')
        ax.set_title('Круговая диаграмма')

        self.canvas.draw()

    # ОПИСЫВАЕМ всё что лочить на время загрузки
    def reaction_update_lock_n_spinner(self, is_loading):
        # 1)
        self.button_load_data.setEnabled(not is_loading)
        # 2)
        self.combo_type_chooser.setEnabled(not is_loading) # - тут попытаюсь разблочить т.к. он начнёт от стейта зависеть после первого фетчинга
        # 3)
        self.button_add_data.setEnabled(not is_loading) # - тут попытаюсь разблочить т.к. он начнёт от стейта зависеть после первого фетчинга
        # 999)
        if is_loading:
            self.graph_spinner.show() 
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