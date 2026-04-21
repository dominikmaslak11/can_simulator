import pytest
from unittest.mock import MagicMock, patch
import threading
from gui.wizard_handlers import WizardHandlers


class MockApp(WizardHandlers):
    """Minimalna klasa symulująca CanSimulatorApp z niezbędnymi atrybutami."""
    def __init__(self):
        self.can = MagicMock()
        self.can.connected = True
        self.binary_frames = []
        self.binary_info = MagicMock()
        self.binary_start_btn = MagicMock()
        self.binary_mode = MagicMock()
        self.binary_interval = MagicMock()
        self.binary_interval.get = MagicMock(return_value=0.1)
        self.hunt_alert_id = MagicMock()
        self.hunt_period = MagicMock()
        self.hunt_tolerance = MagicMock()
        self.hunt_start_index = MagicMock()
        self._redraw_binary_progress = MagicMock()
        self.log = MagicMock()
        self.notebook = MagicMock()
        self.tab_binary = MagicMock()
        self.tab_manual = MagicMock()
        self.manual_id = MagicMock()
        self.manual_data = MagicMock()
        self.manual_extended = MagicMock()
        self.binary_thread = None
        self.binary_progress = MagicMock()
        self.binary_canvas = MagicMock()
        self.binary_yes_btn = MagicMock()
        self.binary_no_btn = MagicMock()
        self.binary_stop_btn = MagicMock()
        self.binary_undo_btn = MagicMock()
        self.quick_test_alert = MagicMock()
        self.wizard_file_label = MagicMock()
        self.wizard_id_listbox = MagicMock()
        self.wizard_alert_result_label = MagicMock()
        self.wizard_deact_result_label = MagicMock()
        self._wizard_awaiting_alert_result = False
        self._wizard_awaiting_deact_result = False

        # Dodajemy brakujące metody, aby mockowanie działało
        self.start_binary_search = MagicMock()
        self._start_hunting = MagicMock()


@pytest.fixture
def app():
    return MockApp()


def test_wizard_browse_file(app, mocker):
    """Test wczytywania pliku przez kreator."""
    mock_filedialog = mocker.patch('gui.wizard_handlers.filedialog')
    mock_filedialog.askopenfilename.return_value = '/path/to/log.txt'
    mock_load = mocker.patch('gui.wizard_handlers.load_frames_from_file')
    mock_load.return_value = [(0x123, b'data', False)] * 10
    mock_refresh = mocker.patch.object(app, 'wizard_refresh_id_list')

    app.wizard_browse_file()

    mock_load.assert_called_once_with('/path/to/log.txt')
    assert len(app.wizard_loaded_frames) == 10
    app.wizard_file_label.config.assert_called_once()
    app.log.assert_called()
    mock_refresh.assert_called_once()


def test_wizard_refresh_id_list_no_frames(app):
    """Test odświeżania listy ID bez wczytanych ramek."""
    with patch('gui.wizard_handlers.messagebox') as mock_msg:
        app.wizard_refresh_id_list()
        mock_msg.showinfo.assert_called_once()


def test_wizard_refresh_id_list_with_frames(app, mocker):
    """Test odświeżania listy ID z ramkami."""
    app.wizard_loaded_frames = [(0x123, b'', False)] * 5 + [(0x1FF, b'', True)] * 3
    mock_profiler = mocker.patch('gui.wizard_handlers.LogProfiler')
    mock_profiler_instance = mock_profiler.return_value
    mock_profiler_instance.get_top_ids.return_value = [(0x123, 5), (0x1FF, 3)]

    app.wizard_refresh_id_list()

    app.wizard_id_listbox.delete.assert_called_once()
    assert app.wizard_id_listbox.insert.call_count == 2
    app.log.assert_called()


def test_wizard_skip_alert_selection(app):
    """Test pomijania wyboru alertu."""
    app.wizard_skip_alert_selection()
    app.wizard_id_listbox.selection_clear.assert_called_once()
    app.log.assert_called()


def test_wizard_start_find_alert_no_frames(app):
    """Test próby wyszukiwania bez wczytanego pliku."""
    with patch('gui.wizard_handlers.messagebox') as mock_msg:
        app.wizard_start_find_alert()
        mock_msg.showerror.assert_called_once()


def test_wizard_start_find_alert_with_selection(app, mocker):
    """Test wyszukiwania z wybranym ID z listy."""
    app.wizard_loaded_frames = [(0x123, b'', False)] * 10
    app.can.connected = True
    app.wizard_id_listbox.curselection.return_value = (0,)
    app.wizard_id_listbox.get.return_value = "0x00000123 (STD) – 10 razy"

    # Mockujemy start_binary_search – teraz metoda istnieje w MockApp
    app.start_binary_search.reset_mock()

    app.wizard_start_find_alert()

    assert app.binary_frames == app.wizard_loaded_frames
    app.binary_info.config.assert_called_once()
    app.binary_start_btn.config.assert_called_with(state='normal')
    app.binary_mode.set.assert_called_with('find_start')
    app._redraw_binary_progress.assert_called_once()
    app.start_binary_search.assert_called_once()
    assert app._wizard_awaiting_alert_result is True


def test_wizard_start_find_alert_manual_id(app, mocker):
    """Test wyszukiwania z ręcznie wpisanym ID."""
    app.wizard_loaded_frames = [(0x123, b'', False)] * 10
    app.can.connected = True
    app.wizard_id_listbox.curselection.return_value = ()
    # Poprawiamy ścieżkę – simpledialog pochodzi z tkinter, nie z wizard_handlers
    mocker.patch('tkinter.simpledialog.askstring', return_value='0x123')
    app.start_binary_search.reset_mock()

    app.wizard_start_find_alert()

    app.start_binary_search.assert_called_once()
    assert app._wizard_awaiting_alert_result is True


def test_wizard_on_alert_found(app):
    """Test aktualizacji etykiety po znalezieniu alertu."""
    app.wizard_on_alert_found(0x123, b'\x01\x02', False)
    app.wizard_alert_result_label.config.assert_called_once()
    assert app.wizard_found_alert == (0x123, b'\x01\x02', False)
    app.log.assert_called()


def test_wizard_test_alert_no_alert(app):
    """Test testowania alertu, gdy alert nie został jeszcze znaleziony."""
    with patch('gui.wizard_handlers.messagebox') as mock_msg:
        app.wizard_test_alert()
        mock_msg.showinfo.assert_called_once()


def test_wizard_test_alert_with_alert(app):
    """Test testowania alertu."""
    app.wizard_found_alert = (0x123, b'\x01\x02', False)
    app.wizard_test_alert()
    app.quick_test_alert.assert_called_once_with(0x123, b'\x01\x02', False, period=1.0, duration=10.0)


def test_wizard_start_hunt_deactivator_no_alert(app):
    """Test polowania bez wcześniejszego znalezienia alertu."""
    with patch('gui.wizard_handlers.messagebox') as mock_msg:
        app.wizard_start_hunt_deactivator()
        mock_msg.showinfo.assert_called_once()


def test_wizard_start_hunt_deactivator_with_alert(app, mocker):
    """Test uruchomienia polowania."""
    app.wizard_found_alert = (0x123, b'\x01\x02', False)
    app.wizard_loaded_frames = [(0x123, b'', False)] * 10
    app.can.connected = True
    app._start_hunting.reset_mock()

    app.wizard_start_hunt_deactivator()

    app.hunt_alert_id.set.assert_called_with('00000123')
    app.hunt_period.set.assert_called_with(1.0)
    app.hunt_tolerance.set.assert_called_with(0.2)
    app.hunt_start_index.set.assert_called_with(0)
    assert app.binary_frames == app.wizard_loaded_frames
    app.binary_mode.set.assert_called_with('hunt_deactivator')
    app._start_hunting.assert_called_once()
    assert app._wizard_awaiting_deact_result is True


def test_wizard_on_deactivator_found(app):
    """Test aktualizacji etykiety po znalezieniu dezaktywatora."""
    candidates = [(0x456, b'\xaa\xbb', True, 1000.0)]
    app.wizard_on_deactivator_found(candidates)
    app.wizard_deact_result_label.config.assert_called_once()
    assert app.wizard_found_deactivator == (0x456, b'\xaa\xbb', True)
    app.log.assert_called()


def test_wizard_test_deactivator_no_deactivator(app):
    """Test testowania dezaktywatora, gdy nie został jeszcze znaleziony."""
    with patch('gui.wizard_handlers.messagebox') as mock_msg:
        app.wizard_test_deactivator()
        mock_msg.showinfo.assert_called_once()


def test_wizard_test_deactivator_with_deactivator(app):
    """Test testowania dezaktywatora."""
    app.wizard_found_deactivator = (0x456, b'\xaa\xbb', True)
    app.wizard_test_deactivator()
    app.quick_test_alert.assert_called_once_with(0x456, b'\xaa\xbb', True, period=1.0, duration=10.0)


def test_wizard_reset(app):
    """Test resetowania kreatora."""
    from gui.tabs.wizard_tab import reset_wizard
    app.wizard_loaded_frames = [(0x123, b'', False)]
    app.wizard_found_alert = (0x123, b'', False)
    app.wizard_found_deactivator = (0x456, b'', False)

    reset_wizard(app)

    app.wizard_file_label.config.assert_called_once()
    app.wizard_id_listbox.delete.assert_called_once()
    app.wizard_alert_result_label.config.assert_called_once()
    app.wizard_deact_result_label.config.assert_called_once()
    assert not hasattr(app, 'wizard_loaded_frames')
    assert not hasattr(app, 'wizard_found_alert')
    assert not hasattr(app, 'wizard_found_deactivator')
    app.log.assert_called()
