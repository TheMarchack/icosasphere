import open3d.visualization.gui as gui


class GuiButton(gui.Button):
    def __init__(self, name, on_clicked_fn):
        super().__init__(name)
        self.set_on_clicked(on_clicked_fn)
        self.horizontal_padding_em = 0.5
        self.vertical_padding_em = 0

class GuiController:
    def __init__(self, name, on_deviation_change_fn, scalar=False):
        self.name = name
        self.scalar = scalar
        self.default_value = 0.0 if not scalar else 1.0
        self.limits = [-5.0, 5.0] if not scalar else [0.0, 2.0]
        self.on_deviation_change_fn = on_deviation_change_fn

        self.reset_button = GuiButton(name, self.set_deviation_value)

        self.num = gui.NumberEdit(gui.NumberEdit.DOUBLE)
        self.num.set_on_value_changed(on_deviation_change_fn)
        self.num.set_value(self.default_value)
        self.num.set_on_value_changed(self.on_num_change)

        self.slider = gui.Slider(gui.Slider.DOUBLE)
        self.slider.set_limits(self.limits[0], self.limits[1])
        self.slider.double_value = self.default_value
        self.slider.set_on_value_changed(self.on_slider_change)

    def set_deviation_value(self, value=None):
        if value is None:
            value = self.default_value
        self.num.set_value(value)
        self.slider.double_value = value
        self.on_deviation_change_fn(value)

    def on_slider_change(self, slider_value):
        self.set_deviation_value(slider_value)
        self.on_deviation_change_fn(slider_value)

    def on_num_change(self, num_value):
        # Limit the value to allowed range
        num_value = max(num_value, self.limits[0])
        num_value = min(num_value, self.limits[1])

        self.set_deviation_value(num_value)
        self.on_deviation_change_fn(num_value)
