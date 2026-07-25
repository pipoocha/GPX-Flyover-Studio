import pyvista as pv

plotter = pv.Plotter()
sphere = pv.Sphere(radius=1.0)

plotter.add_mesh(sphere, color="orange")
plotter.add_text("PyVista OK", font_size=18)

plotter.show()