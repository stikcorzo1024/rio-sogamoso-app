"""App de prueba simple para verificar que Kivy funciona en Android."""
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout


class TestApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')
        label = Label(
            text='Rio Sogamoso\n\nSi ves esto, Kivy funciona!',
            font_size='24sp',
            halign='center'
        )
        layout.add_widget(label)
        return layout


if __name__ == '__main__':
    TestApp().run()
