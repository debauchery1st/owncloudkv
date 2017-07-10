KV = """
<OwnCloudPopup>:
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        Rectangle:
            pos: self.pos
            size: self.size
            source: app.fin_pic

<OwnCloudLayout>:
    oc_backup: oc_backup
    oc_update: oc_update
    oc_status: oc_status
    orientation: 'vertical'
    padding: self.width*.05, self.height*.05, self.width*.05, self.height*.05
    spacing: '20dp'
    canvas.before:
        Rectangle:
            pos: self.pos
            size: self.size
            source: 'bkg.jpg'
    Label:
        id: oc_widget
        text: 'ownCloud'
        font_name: 'PoiretOne-Regular.ttf'
        font_size: '32sp'
        size_hint_y: None
    Label:
        id: oc_status
        text: self.parent.status_label
        font_name: 'PoiretOne-Regular.ttf'
        font_size: '16sp'
        size_hint_y: None
    ProgressBar:
        id: oc_progress
        value: self.parent.oc_progress_current
        max: self.parent.oc_progress_total
    Button:
        id: oc_update
        text: 'Update'
        font_name: 'PoiretOne-Regular.ttf'
        font_size: '20sp'
        on_press: self.parent.download(self)
    Button:
        id: oc_backup
        text: 'Backup'
        font_name: 'PoiretOne-Regular.ttf'
        font_size: '20sp'
        on_press: self.parent.upload(self)
    Button:
        id: oc_settings
        text: 'Settings'
        font_name: 'PoiretOne-Regular.ttf'
        font_size: '20sp'
        on_press: app.open_settings()
    Button:
        id: oc_exit
        text: 'Exit ownCloud'
        font_name: 'PoiretOne-Regular.ttf'
        font_size: '20sp'
        on_press: app.stop()
"""