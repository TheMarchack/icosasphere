# ----------------------------------------------------------------------------
# -                        Open3D: www.open3d.org                            -
# ----------------------------------------------------------------------------
# Copyright (c) 2018-2023 www.open3d.org
# SPDX-License-Identifier: MIT
# ----------------------------------------------------------------------------

import json
import numpy as np
import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import os
import platform
import sys

from controls import GuiButton

isMacOS = (platform.system() == "Darwin")


class Settings:
    def __init__(self):
        self.mouse_model = gui.SceneWidget.Controls.ROTATE_CAMERA
        self.bg_color = 0.2
        self.post_process = True
        self.show_axes = False

        # Set up material properties for point cloud
        self._point_cloud_material = rendering.MaterialRecord()
        self._point_cloud_material.base_color = [0.85, 0.85, 0.85, 1.0]
        self._point_cloud_material.point_size = 1

        # Set up material properties for camera geometry
        self._camera_material = rendering.MaterialRecord()
        self._camera_material.shader = "unlitLine"
        self._camera_material.line_width = 1
        self._camera_material.point_size = 2


class AppWindow:
    MENU_OPEN = 1
    MENU_EXPORT = 2
    MENU_QUIT = 3
    MENU_SHOW_SETTINGS = 11
    MENU_ABOUT = 21

    def __init__(self, width, height):
        self.settings = Settings()

        self.window = gui.Application.instance.create_window(
            "Open3D", width, height)

        # 3D widget
        self._scene = gui.SceneWidget()
        self._scene.scene = rendering.Open3DScene(self.window.renderer)
        self._scene.set_view_controls(self.settings.mouse_model)

        # Turning off post-processing makes the image very grainy
        self._scene.scene.view.set_post_processing(self.settings.post_process)
        # Adjusting the quality settings makes image nicer to look at
        self._scene.scene.view.set_antialiasing(False)
        color_grading = rendering.ColorGrading(rendering.ColorGrading.Quality.ULTRA,
                                               rendering.ColorGrading.ToneMapping.LINEAR)
        self._scene.scene.view.set_color_grading(color_grading)

        # --- Settings ---
        self._prepare_settings_panel()

        # ---- Menu ----
        self._prepare_menu()

        # Create the Icosasphere
        self._create_icosasphere()

        self._apply_settings()

    def _prepare_settings_panel(self):
        # Prepare size values for panel relative to font size (works on varied DPI)
        em = self.window.theme.font_size
        separation = int(round(0.25 * em))

        # Prepare Vertical layout for settings panel
        self._settings_panel = gui.Vert(
            0, gui.Margins(separation, separation, separation, separation))

        # Each section of settings is a collapsable vertical layout
        self._prepare_view_controls(separation)
        self._prepare_icosasphere(separation)

        # Set up the settings panel layout by adding on_layout callback and adding children
        self.window.set_on_layout(self._on_layout)
        self.window.add_child(self._scene)
        self.window.add_child(self._settings_panel)

    def _prepare_view_controls(self, separation):
        view_ctrls = gui.CollapsableVert("View controls", separation,
                                         gui.Margins(separation, 0, 0, 0))
        view_ctrls.set_is_open(False)

        # Prepare buttons for changing mouse mode
        self._sphere_button = GuiButton("Sphere", self._set_mouse_mode_rotate_sphere)
        self._arcball_button = GuiButton("Arcball", self._set_mouse_mode_rotate)
        self._fly_button = GuiButton("Fly", self._set_mouse_mode_fly)
        # Add them to the layout
        view_ctrls.add_child(gui.Label("Mouse controls"))
        h = gui.Horiz(separation)
        h.add_stretch()
        h.add_child(self._sphere_button)
        h.add_child(self._arcball_button)
        h.add_child(self._fly_button)
        h.add_stretch()
        view_ctrls.add_child(h)

        # Add Checkboxes for Axes and Image Post Processing
        self._show_axes = gui.Checkbox("Show axes")
        self._show_axes.set_on_checked(self._on_show_axes)
        self._post_process = gui.Checkbox("Post Process")
        self._post_process.set_on_checked(self._on_post_process)
        view_ctrls.add_fixed(separation)
        h = gui.Horiz(separation)
        h.add_child(self._show_axes)
        h.add_child(self._post_process)
        view_ctrls.add_child(h)
        view_ctrls.add_fixed(separation)

        # Add the view controls to the settings panel
        self._settings_panel.add_child(view_ctrls)

    def _prepare_icosasphere(self, separation):
        # Make a button to reset the icosphere
        self.reset = GuiButton("Reset", self._on_reset_icosasphere)

        # Prepare the subdivisions slider for the icosphere
        self.subdivisions = gui.Slider(gui.Slider.INT)
        self.subdivisions.set_limits(0, 6)
        self.subdivisions.int_value = 0
        self.subdivisions.set_on_value_changed(self._on_subdivisions_change)

        # Add Deviation buttons and sliders to the settings panel
        icosphere_ctrls = gui.CollapsableVert("Icosasphere", separation,
                                        gui.Margins(separation, 0, 0, 0))
        icosphere_ctrls.set_is_open(True)

        # Add the icosasphere controls
        icosphere_ctrls.add_child(self.reset)
        icosphere_ctrls.add_child(self.subdivisions)
        icosphere_ctrls.add_fixed(separation)

        # Add the deviations to the settings panel
        self._settings_panel.add_child(icosphere_ctrls)

    def _prepare_menu(self):
        # The menu is global (because the macOS menu is global), so only create
        # it once, no matter how many windows are created
        if gui.Application.instance.menubar is None:
            if isMacOS:
                app_menu = gui.Menu()
                app_menu.add_item("About", AppWindow.MENU_ABOUT)
                app_menu.add_separator()
                app_menu.add_item("Quit", AppWindow.MENU_QUIT)
            file_menu = gui.Menu()
            file_menu.add_item("Open...", AppWindow.MENU_OPEN)
            file_menu.add_item("Export Current Image...", AppWindow.MENU_EXPORT)
            if not isMacOS:
                file_menu.add_separator()
                file_menu.add_item("Quit", AppWindow.MENU_QUIT)
            settings_menu = gui.Menu()
            settings_menu.add_item("Controls", AppWindow.MENU_SHOW_SETTINGS)
            settings_menu.set_checked(AppWindow.MENU_SHOW_SETTINGS, True)
            help_menu = gui.Menu()
            help_menu.add_item("About", AppWindow.MENU_ABOUT)

            menu = gui.Menu()
            if isMacOS:
                # macOS will name the first menu item for the running application
                # (in our case, probably "Python"), regardless of what we call
                # it. This is the application menu, and it is where the
                # About..., Preferences..., and Quit menu items typically go.
                menu.add_menu("Example", app_menu)
                menu.add_menu("File", file_menu)
                menu.add_menu("Settings", settings_menu)
                # Don't include help menu unless it has something more than
                # About...
            else:
                menu.add_menu("File", file_menu)
                menu.add_menu("Settings", settings_menu)
                menu.add_menu("Help", help_menu)
            gui.Application.instance.menubar = menu

        # The menubar is global, but we need to connect the menu items to the
        # window, so that the window can call the appropriate function when the
        # menu item is activated.
        self.window.set_on_menu_item_activated(AppWindow.MENU_OPEN, self._on_menu_open)
        self.window.set_on_menu_item_activated(AppWindow.MENU_EXPORT,
                                     self._on_menu_export)
        self.window.set_on_menu_item_activated(AppWindow.MENU_QUIT, self._on_menu_quit)
        self.window.set_on_menu_item_activated(AppWindow.MENU_SHOW_SETTINGS,
                                     self._on_menu_toggle_settings_panel)
        self.window.set_on_menu_item_activated(AppWindow.MENU_ABOUT, self._on_menu_about)

    def _create_icosasphere(self, subdivisions=0):
        # Remove existing
        print("Removing existing geometry")
        self._scene.scene.remove_geometry("Icosasphere")

        # Golden ratio
        PHI = (1 + np.sqrt(5)) / 2

        # Vertices of an icosahedron
        vertices = [
            (-1, PHI, 0), (1, PHI, 0), (-1, -PHI, 0), (1, -PHI, 0),
            (0, -1, PHI), (0, 1, PHI), (0, -1, -PHI), (0, 1, -PHI),
            (PHI, 0, -1), (PHI, 0, 1), (-PHI, 0, -1), (-PHI, 0, 1)
        ]
        vertices /= np.linalg.norm(vertices, axis=1)[:, np.newaxis]

        # Faces of the icosahedron
        faces = [
            (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
            (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
            (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
            (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)
        ]

        print("Managing subdivisions")
        # Subdivide triangles
        for _ in range(subdivisions):
            new_faces = []
            vertex_map = {}
            index = len(vertices)

            def get_vertex(v1, v2):
                nonlocal vertices, index
                key = tuple(sorted([v1, v2]))
                if key in vertex_map:
                    return vertex_map[key]
                else:
                    new_vertex = (vertices[v1] + vertices[v2]) / 2
                    vertices = np.vstack([vertices, new_vertex])  # Add new vertex
                    vertex_map[key] = index
                    index += 1
                    return vertex_map[key]

            for v1, v2, v3 in faces:
                a = get_vertex(v1, v2)
                b = get_vertex(v2, v3)
                c = get_vertex(v3, v1)
                new_faces.extend([
                    (v1, a, c),
                    (v2, b, a),
                    (v3, c, b),
                    (a, b, c)
                ])
            faces = new_faces

        print("Creating line set")
        # Create line set for visualization
        lines = set()
        for v1, v2, v3 in faces:
            lines.update([(v1, v2), (v2, v3), (v3, v1)])

        # Normalize vertices
        vertices /= np.linalg.norm(vertices, axis=1)[:, np.newaxis]

        print("Creating LineSet")
        self.icosasphere = o3d.geometry.LineSet(
            points=o3d.utility.Vector3dVector(vertices),
            lines=o3d.utility.Vector2iVector(list(lines))
        )

        print("Adding geometry")
        self._scene.scene.add_geometry("Icosasphere", self.icosasphere,
                                       self.settings._camera_material)
        print("Setting up camera")
        bounds = self._scene.scene.bounding_box
        self._scene.setup_camera(60, bounds, bounds.get_center())
        self._scene.force_redraw()

    def _apply_settings(self):
        bg_color = [
            self.settings.bg_color, self.settings.bg_color,
            self.settings.bg_color, 1.0
        ]
        self._scene.scene.set_background(bg_color)
        self._scene.scene.view.set_post_processing(self.settings.post_process)
        self._scene.scene.show_axes(self.settings.show_axes)

        self._post_process.checked = self.settings.post_process
        self._show_axes.checked = self.settings.show_axes

    def _on_layout(self, layout_context):
        # The on_layout callback should set the frame (position + size) of every
        # child correctly. After the callback is done the window will layout
        # the grandchildren.
        r = self.window.content_rect
        self._scene.frame = r
        width = 17 * layout_context.theme.font_size
        height = min(
            r.height,
            self._settings_panel.calc_preferred_size(
                layout_context, gui.Widget.Constraints()).height)
        self._settings_panel.frame = gui.Rect(r.get_right() - width, r.y, width,
                                              height)

    def _set_mouse_mode_rotate_sphere(self):
        self._scene.set_view_controls(gui.SceneWidget.Controls.ROTATE_CAMERA_SPHERE)

    def _set_mouse_mode_rotate(self):
        self._scene.set_view_controls(gui.SceneWidget.Controls.ROTATE_CAMERA)

    def _set_mouse_mode_fly(self):
        self._scene.set_view_controls(gui.SceneWidget.Controls.FLY)

    def _on_post_process(self, post_process):
        self.settings.post_process = post_process
        self._apply_settings()

    def _on_show_axes(self, show):
        self.settings.show_axes = show
        self._apply_settings()

    def _on_reset_icosasphere(self):
        print("Resetting")
        self.subdivisions.int_value = 0
        self._create_icosasphere()

    def _on_subdivisions_change(self, subdivisions):
        print("Changing")
        print("Subdivisions", int(subdivisions))
        self._create_icosasphere(int(subdivisions))

    def _on_menu_open(self):
        dlg = gui.FileDialog(gui.FileDialog.OPEN, "Choose file to load",
                             self.window.theme)
        dlg.add_filter(".ply", "Point Cloud files (.ply)")
        dlg.add_filter(".json", "Json files for camera configuration (.json)")

        dlg.add_filter("", "All files")

        # A file dialog MUST define on_cancel and on_done functions
        dlg.set_on_cancel(self._on_file_dialog_cancel)
        dlg.set_on_done(self._on_load_dialog_done)
        self.window.show_dialog(dlg)

    def _on_file_dialog_cancel(self):
        self.window.close_dialog()

    def _on_load_dialog_done(self, filename):
        self.window.close_dialog()
        self.load(filename)

    def _on_menu_export(self):
        dlg = gui.FileDialog(gui.FileDialog.SAVE, "Choose file to save",
                             self.window.theme)
        dlg.add_filter(".png", "PNG files (.png)")
        dlg.set_on_cancel(self._on_file_dialog_cancel)
        dlg.set_on_done(self._on_export_dialog_done)
        self.window.show_dialog(dlg)

    def _on_export_dialog_done(self, filename):
        self.window.close_dialog()
        self.export_image(filename)

    def _on_menu_quit(self):
        gui.Application.instance.quit()

    def _on_menu_toggle_settings_panel(self):
        self._settings_panel.visible = not self._settings_panel.visible
        gui.Application.instance.menubar.set_checked(
            AppWindow.MENU_SHOW_SETTINGS, self._settings_panel.visible)

    def _on_menu_about(self):
        # Show a simple dialog. Although the Dialog is actually a widget, you can
        # treat it similar to a Window for layout and put all the widgets in a
        # layout which you make the only child of the Dialog.
        em = self.window.theme.font_size
        dlg = gui.Dialog("About")

        # Add the text
        dlg_layout = gui.Vert(em, gui.Margins(em, em, em, em))
        dlg_layout.add_child(gui.Label("Point Cloud Simulator GUI v1.2"))

        # Add the Ok button. We need to define a callback function to handle
        # the click.
        ok = gui.Button("OK")
        ok.set_on_clicked(self._on_about_ok)

        # We want the Ok button to be an the right side, so we need to add
        # a stretch item to the layout, otherwise the button will be the size
        # of the entire row. A stretch item takes up as much space as it can,
        # which forces the button to be its minimum size.
        h = gui.Horiz()
        h.add_stretch()
        h.add_child(ok)
        h.add_stretch()
        dlg_layout.add_child(h)

        dlg.add_child(dlg_layout)
        self.window.show_dialog(dlg)

    def _on_about_ok(self):
        self.window.close_dialog()

    def load(self, filename):
        pass

    def export_image(self, path):

        def on_image(image):
            img = image

            quality = 9  # png
            if path.endswith(".jpg"):
                quality = 100
            o3d.io.write_image(path, img, quality)

        self._scene.scene.scene.render_to_image(on_image)

def main():
    # We need to initialize the application, which finds the necessary shaders
    # for rendering and prepares the cross-platform window abstraction.
    gui.Application.instance.initialize()

    w = AppWindow(1024, 768)

    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.exists(path):
            w.load(path)
        else:
            w.window.show_message_box("Error",
                                      "Could not open file '" + path + "'")

    # Run the event loop. This will not return until the last window is closed.
    gui.Application.instance.run()


if __name__ == "__main__":
    main()
