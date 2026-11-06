import sys
import tkinter as tk


def enable_native_dpi():
    if sys.platform != "win32":
        return
    import ctypes
    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError):
        pass
    try:
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def display_metrics(root):
    dpi = root.winfo_fpixels("1i")
    width, height = root.winfo_screenwidth(), root.winfo_screenheight()
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        handle = wintypes.HWND(root.winfo_id())
        try:
            user32.GetDpiForWindow.argtypes = [wintypes.HWND]
            dpi = user32.GetDpiForWindow(handle) or dpi
        except (AttributeError, OSError):
            pass
        try:
            class MonitorInfo(ctypes.Structure):
                _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                            ("work", wintypes.RECT), ("flags", wintypes.DWORD)]
            user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
            user32.MonitorFromWindow.restype = wintypes.HANDLE
            user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
            monitor = user32.MonitorFromWindow(handle, 2)
            info = MonitorInfo()
            info.size = ctypes.sizeof(info)
            if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                width, height = info.work.right - info.work.left, info.work.bottom - info.work.top
        except (AttributeError, OSError):
            pass
    native = max(.75, dpi / 96)
    scale = max(.5, min(native, (width - 24 * native) / 1000, (height - 48 * native) / 740))
    return round(scale, 4), width, height


class ScaledGeometry:
    pixel_options = {"padx", "pady", "borderwidth", "bd", "highlightthickness", "wraplength"}

    def _init_geometry(self, theme, options):
        self._ui_theme = theme
        self._logical_options = {key: value for key, value in options.items() if key in self.pixel_options}
        self._logical_geometry = {}
        theme._geometry.add(self)
        return self._scale_options(options, self.pixel_options)

    def _scale_options(self, options, names):
        def scaled(value):
            if isinstance(value, (tuple, list)):
                return tuple(scaled(part) for part in value)
            if isinstance(value, (int, float)):
                return round(value * self._ui_theme.scale)
            return value
        return {key: scaled(value) if key in names else value for key, value in options.items()}

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        self._logical_options.update({key: value for key, value in kwargs.items() if key in self.pixel_options})
        return super().configure(cnf, **self._scale_options(kwargs, self.pixel_options))

    config = configure

    def _geometry_call(self, method, cnf, kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
            cnf = None
        self._logical_geometry.setdefault(method, {}).update(kwargs)
        names = {"padx", "pady", "ipadx", "ipady"}
        if method == "place_configure":
            names |= {"x", "y", "width", "height"}
        return getattr(super(), method)(cnf or {}, **self._scale_options(kwargs, names))

    def pack_configure(self, cnf=None, **kwargs):
        return self._geometry_call("pack_configure", cnf, kwargs)

    pack = pack_configure

    def grid_configure(self, cnf=None, **kwargs):
        return self._geometry_call("grid_configure", cnf, kwargs)

    grid = grid_configure

    def place_configure(self, cnf=None, **kwargs):
        return self._geometry_call("place_configure", cnf, kwargs)

    place = place_configure

    def _reflow(self):
        super().configure(**self._scale_options(self._logical_options, self.pixel_options))
        method = self.winfo_manager() + "_configure"
        if method in self._logical_geometry:
            self._geometry_call(method, None, self._logical_geometry[method].copy())


class LayoutFrame(ScaledGeometry, tk.Frame):
    pixel_options = ScaledGeometry.pixel_options | {"width", "height"}

    def __init__(self, parent, theme, **kwargs):
        super().__init__(parent, **self._init_geometry(theme, kwargs))


class LayoutLabel(ScaledGeometry, tk.Label):
    def __init__(self, parent, theme, **kwargs):
        super().__init__(parent, **self._init_geometry(theme, kwargs))


class LayoutEntry(ScaledGeometry, tk.Entry):
    def __init__(self, parent, theme, **kwargs):
        super().__init__(parent, **self._init_geometry(theme, kwargs))
