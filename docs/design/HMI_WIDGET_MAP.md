# HMI-01 — mapa widgetów i połączeń

Plik generowany: `python tools/hmi_inventory.py`. Nie edytować ręcznie.
Pełny kontrakt i ograniczenia: [HMI_BASELINE.md](HMI_BASELINE.md).

## Źródła

| Plik | SHA-256 |
| --- | --- |
| screens/linumert/linumert.ui | 281d62c70697f30b00aadb419b3143111a4508c3a57467ea7130d5da2488ec67 |
| screens/linumert/linumert_handler.py | ca147ceffdfcf3b85bfeb6190c5c87ffe0d25163db1dc7099de453f96fac915f |
| screens/linumert/linumert_upstream_handler.py | 0f86be6c0eb7c275ac104b60365cda277b76e68cf1ec2bc815cc2f0ffb0ccc51 |

## Widgety (421)

| Nazwa | Klasa | Rodzic | Właściwości UI |
| --- | --- | --- | --- |
| MainWindow | QMainWindow | — | geometry=0 0 1280 933; sizePolicy=0 0; minimumSize=1280 768; maximumSize=1700 1200; windowTitle=QT Dragon 2.0; autoFillBackground=false; styleSheet= |
| centralwidget | QWidget | MainWindow | sizePolicy=0 0; minimumSize=1280 768; maximumSize=1700 1200 |
| screen_options | ScreenOptions | centralwidget | sizePolicy=0 0; minimumSize=0 0; maximumSize=16777215 16777215; notify_option=true; catch_close_option=true; close_overlay_color=212 0 0; catch_errors_option=true; play_sounds_option=false; use_pref_file_option=true; pref_filename_string=~/linuxcnc/configs/linumert/linumert.pref; embedded_program_option=true; focusEffect_option=true; focusBlur_option=false; focusTint_option=false; entryDialog_option=true; entryDialogSoftkey_option=false; toolDialog_option=true; tool_overlay_color=0 0 255; fileDialog_option=true; toolOffsetDialog_option=false; originOffsetDialog_option=true; calculatorDialog_option=true; machineLogDialog_option=true; runFromLineDialog_option=true |
| frame_buttonbar | QFrame | screen_options | sizePolicy=0 0; minimumSize=0 0; maximumSize=16777215 48; frameShape=QFrame::Box; frameShadow=QFrame::Raised |
| btn_main | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=MAIN; checkable=true; checked=true; index=0; buttonGroup=page_buttonGroup |
| btn_file | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=FILE; checkable=true; index=1; buttonGroup=page_buttonGroup |
| btn_offsets | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=OFFSETS; checkable=true; index=2; buttonGroup=page_buttonGroup |
| btn_tool | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=TOOL; checkable=true; index=3; buttonGroup=page_buttonGroup |
| btn_status | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=STATUS; checkable=true; index=4; buttonGroup=page_buttonGroup |
| btn_probe | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=PROBE; checkable=true; index=5; buttonGroup=page_buttonGroup |
| btn_camera | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=CAMERA; checkable=true; index=6; buttonGroup=page_buttonGroup |
| btn_gcodes | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=GCODES; checkable=true; index=7; buttonGroup=page_buttonGroup |
| btn_setup | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=SETUP; checkable=true; index=8; buttonGroup=page_buttonGroup |
| btn_settings | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=SETTINGS; checkable=true; index=9; buttonGroup=page_buttonGroup |
| btn_utils | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=UTILS; checkable=true; index=10; buttonGroup=page_buttonGroup |
| btn_user | QPushButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; text=USER; checkable=true; index=11; buttonGroup=page_buttonGroup |
| action_machine_on | ActionButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; baseSize=0 0; toolTip=Toggle machine state; text=MACHINE OFF; iconSize=100 40; checkable=true; checked=false; flat=false; indicator_option=false; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=true; on_color=0 255 0; shape_option=1; off_color=255 0 0; indicator_size=0.200000000000000; right_edge_offset=6; top_edge_offset=6; true_state_string=MACHINE ON; false_state_string=MACHINE OFF; is_on_status=true; machine_on_action=true |
| action_estop | ActionButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; baseSize=0 0; text=ESTOP RESET; iconSize=0 0; checkable=true; checked=false; indicator_option=false; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=true; on_color=0 255 0; shape_option=1; off_color=255 0 0; indicator_size=0.200000000000000; right_edge_offset=6; top_edge_offset=6; true_state_string=ESTOP SET; false_state_string=ESTOP RESET; invert_the_status=true; is_estopped_status=true; estop_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=p; command_text_string=; ini_mdi_number=0; textTemplate=; alt_textTemplate=%1.2f mm |
| action_exit | ActionButton | frame_buttonbar | sizePolicy=0 0; minimumSize=74 40; maximumSize=74 40; baseSize=0 0; toolTip=Exit LinuxCNC; text=EXIT; exit_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| widget_graphics | QWidget | screen_options | sizePolicy=0 0 |
| widget | QWidget | widget_graphics |  |
| splitter_h | QSplitter | widget | orientation=Qt::Horizontal; opaqueResize=true; handleWidth=2; childrenCollapsible=true |
| frame_top_left | QFrame | splitter_h | sizePolicy=0 0; minimumSize=368 0; maximumSize=16777215 16777215; frameShape=QFrame::Box; frameShadow=QFrame::Raised |
| stackedWidget | QStackedWidget | frame_top_left | sizePolicy=0 0; minimumSize=0 30; maximumSize=16777215 16777215; frameShape=QFrame::Box; frameShadow=QFrame::Raised; currentIndex=3 |
| gcode_page | QWidget | stackedWidget | sizePolicy=0 0; minimumSize=0 0; maximumSize=16777215 16777215 |
| cmb_gcode_history | QComboBox | gcode_page | minimumSize=0 30; maximumSize=16777215 30; font=Lato Heavy 10 50 false false; focusPolicy=Qt::ClickFocus; toolTip=History of loaded GCODE programs; editable=false; currentText=; maxCount=100; insertPolicy=QComboBox::InsertAtTop |
| gcode_viewer | GcodeEditor | gcode_page | sizePolicy=0 0; minimumSize=0 0; maximumSize=16777215 16777215; font=Lato 10 75 true; auto_show_mdi_status=true; auto_show_manual_status=false |
| file_page | QWidget | stackedWidget |  |
| filemanager_usb | FileManager | file_page | sizePolicy=0 0 |
| offset_page | QWidget | stackedWidget |  |
| widget_work_height | QWidget | offset_page |  |
| label_46 | QLabel | widget_work_height | sizePolicy=0 0; minimumSize=160 30; maximumSize=160 30; toolTip=Distance from machine bed to top of workpiece; midLineWidth=0; text=WORKPIECE HEIGHT; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; margin=0; indent=8 |
| lineEdit_work_height | QLineEdit | widget_work_height | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; maxLength=8; alignment=Qt::AlignCenter |
| lbl_tool_sensor_B2W | QLabel | widget_work_height | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; text=MM; alignment=Qt::AlignCenter |
| widget_sensor_height | QWidget | offset_page |  |
| label_16 | QLabel | widget_sensor_height | sizePolicy=0 0; minimumSize=160 30; maximumSize=16777215 160; toolTip=Distance from machine bed to top of tool sensor; midLineWidth=0; text=TOOL SENSOR HEIGHT; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; margin=0; indent=8 |
| lineEdit_sensor_height | QLineEdit | widget_sensor_height | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; toolTip=; maxLength=8; alignment=Qt::AlignCenter; clearButtonEnabled=false |
| lbl_tool_sensor_B2S | QLabel | widget_sensor_height | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; text=MM; alignment=Qt::AlignCenter |
| label_45 | QLabel | offset_page | focusPolicy=Qt::NoFocus; text=; pixmap=:/images/images/tool_probe.png; alignment=Qt::AlignHCenter&#124;Qt::AlignTop |
| horizontalWidget | QWidget | offset_page | sizePolicy=0 0; minimumSize=0 30; maximumSize=16777215 30 |
| label_49 | QLabel | horizontalWidget | sizePolicy=0 0; minimumSize=180 30; maximumSize=180 30; text=; alignment=Qt::AlignCenter |
| label_15 | QLabel | horizontalWidget | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; text=X; alignment=Qt::AlignCenter |
| label_48 | QLabel | horizontalWidget | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; text=Y; alignment=Qt::AlignCenter |
| label_70 | QLabel | horizontalWidget | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30 |
| widget_sensor_location | QWidget | offset_page |  |
| label_8 | QLabel | widget_sensor_location | sizePolicy=0 0; minimumSize=180 30; maximumSize=180 30; text=TOOL SENSOR LOCATION; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; indent=8 |
| lineEdit_sensor_x | QLineEdit | widget_sensor_location | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; maxLength=8; alignment=Qt::AlignCenter; readOnly=false |
| lineEdit_sensor_y | QLineEdit | widget_sensor_location | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; maxLength=8; alignment=Qt::AlignCenter; readOnly=false |
| lbl_tool_sensor_loc | QLabel | widget_sensor_location | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; text=MM; alignment=Qt::AlignCenter |
| widget_laser_offset | QWidget | offset_page |  |
| label_33 | QLabel | widget_laser_offset | sizePolicy=0 0; minimumSize=180 30; maximumSize=180 30; text=LASER OFFSET; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; indent=8 |
| lineEdit_laser_x | QLineEdit | widget_laser_offset | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; maxLength=8; alignment=Qt::AlignCenter; readOnly=false |
| lineEdit_laser_y | QLineEdit | widget_laser_offset | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; maxLength=8; alignment=Qt::AlignCenter; readOnly=false |
| lbl_laser_offset | QLabel | widget_laser_offset | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; text=MM; alignment=Qt::AlignCenter |
| widget_camera_offset | QWidget | offset_page |  |
| label_63 | QLabel | widget_camera_offset | sizePolicy=0 0; minimumSize=180 30; maximumSize=180 30; text=CAMERA OFFSET; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; indent=8 |
| lineEdit_camera_x | QLineEdit | widget_camera_offset | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; maxLength=8; alignment=Qt::AlignCenter |
| lineEdit_camera_y | QLineEdit | widget_camera_offset | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; maxLength=8; alignment=Qt::AlignCenter |
| lbl_camera_offset | QLabel | widget_camera_offset | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; text=MM; alignment=Qt::AlignCenter |
| widget_offset_buttons | QWidget | offset_page |  |
| btn_goto_sensor | QPushButton | widget_offset_buttons | sizePolicy=0 0; minimumSize=66 50; maximumSize=78 50; toolTip=Go to Tool Sensor location; text=GO TO SENSOR |
| btn_laser_on | PushButton | widget_offset_buttons | sizePolicy=0 0; minimumSize=66 50; maximumSize=78 50; toolTip=Toggle laser crosshairs; text=LASER OFF; checkable=true; checked=false; pin_name=btn-laser-on; indicator_option=false; checked_state_text_option=true; python_command_option=false; on_color=0 255 0; indicator_size=0.200000000000000; true_state_string=LASER ON; false_state_string=LASER OFF; true_python_cmd_string=print"Laser crosshair turned on"; false_python_cmd_string=print"Laser crosshair turned off" |
| btn_ref_laser | QPushButton | widget_offset_buttons | sizePolicy=0 0; minimumSize=66 50; maximumSize=78 50; toolTip=Set laser crosshair reference; text=REF LASER |
| btn_ref_camera | QPushButton | widget_offset_buttons | sizePolicy=0 0; minimumSize=66 50; maximumSize=78 50; text=REF CAMERA |
| btn_touch_sensor | QPushButton | widget_offset_buttons | sizePolicy=0 0; minimumSize=66 50; maximumSize=78 50; statusTip=TOUCHOFF TO TOOL SENSOR; text=TOOL SENSOR; sensor=_toolsensor_ |
| tool_page | QWidget | stackedWidget |  |
| label_58 | QLabel | tool_page | sizePolicy=0 0; minimumSize=50 30; maximumSize=50 30; text=TOOL; alignment=Qt::AlignCenter |
| statuslabel_2 | StatusLabel | tool_page | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; alignment=Qt::AlignCenter; tool_number_status=true |
| label_2 | QLabel | tool_page | text=; pixmap=:/images/images/atc_spindle_tool.png; alignment=Qt::AlignBottom&#124;Qt::AlignHCenter |
| widget_tool_diameter | QWidget | tool_page |  |
| label_10 | QLabel | widget_tool_diameter | sizePolicy=0 0; minimumSize=154 0; maximumSize=154 16777215; text=TOOL DIAMETER; alignment=Qt::AlignCenter |
| status_tool_dia | StatusLabel | widget_tool_diameter | sizePolicy=0 0; minimumSize=65 30; maximumSize=60 30; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; alignment=Qt::AlignCenter; textTemplate=%5.3f; alt_textTemplate=%10.3f; tool_diameter_status=true |
| statelabel | StateLabel | widget_tool_diameter | minimumSize=50 30; maximumSize=50 30; frameShadow=QFrame::Sunken; alignment=Qt::AlignCenter; true_textTemplate=MM; false_textTemplate=INCH |
| widget_touch_height | QWidget | tool_page |  |
| label_9 | QLabel | widget_touch_height | sizePolicy=0 0; minimumSize=154 30; maximumSize=154 30; toolTip=Distance from machine bed to top of touch plate; text=TOUCH PLATE HEIGHT; alignment=Qt::AlignCenter |
| lineEdit_touch_height | QLineEdit | widget_touch_height | sizePolicy=0 0; minimumSize=65 30; maximumSize=60 30; maxLength=8; frame=true; alignment=Qt::AlignCenter; readOnly=false |
| lbl_touchheight_units | QLabel | widget_touch_height | sizePolicy=0 0; minimumSize=50 30; maximumSize=50 30; text=MM; alignment=Qt::AlignCenter; wordWrap=false; indent=0 |
| label_12 | QLabel | widget_touch_height | minimumSize=50 0; maximumSize=50 16777215; text=PROBE; alignment=Qt::AlignCenter |
| led_probe | LED | widget_touch_height | minimumSize=20 0; maximumSize=20 16777215; pin_name=led-probe; diameter=17; color=0 255 0 |
| widget_tool_table | QWidget | tool_page |  |
| btn_tool_add | IndicatedPushButton | widget_tool_table | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; toolTip=Add new tool to tooltable; text=ADD; python_command_option=true; true_python_cmd_string=INSTANCE.tooloffsetview.add_tool(); false_python_cmd_string= |
| btn_tool_delete | IndicatedPushButton | widget_tool_table | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; toolTip=Delete selected tools; text=DELETE; python_command_option=true; true_python_cmd_string=INSTANCE.tooloffsetview.delete_tools(); false_python_cmd_string= |
| btn_m61 | QPushButton | widget_tool_table | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; toolTip=Load selected tool; text=M61 Qn |
| btn_touchplate | QPushButton | widget_tool_table | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; statusTip=TOUCHOFF TO TOOL TOUCHPLATE; text=TOUCH PLATE; sensor=_touchplate_ |
| ngcgui_page | QWidget | stackedWidget |  |
| mdiline | MDILine | frame_top_left | sizePolicy=0 0; minimumSize=0 30; maximumSize=16777215 32; maxLength=100; placeholderText=MDI:; soft_keyboard_option=false |
| frm_backplot | QFrame | splitter_h | sizePolicy=0 0; minimumSize=540 0; maximumSize=16777215 16777215; baseSize=0 0; frameShape=QFrame::Box; frameShadow=QFrame::Raised; lineWidth=1 |
| stackedWidget_mainTab | QStackedWidget | frm_backplot | sizePolicy=0 0; minimumSize=500 0; maximumSize=1677725 16777215; frameShape=QFrame::NoFrame; frameShadow=QFrame::Raised; currentIndex=0 |
| stackedWidget_mainTabPage1 | QWidget | stackedWidget_mainTab |  |
| widget_view_buttons | QWidget | stackedWidget_mainTabPage1 | sizePolicy=0 0; minimumSize=54 0; maximumSize=54 16777215 |
| actiontoolbutton | ActionToolButton | widget_view_buttons | minimumSize=50 40; maximumSize=50 40; toolTip=Hold to save current view; text=User View; checkable=true; autoExclusive=true; autoRaise=false; arrowType=Qt::NoArrow |
| actionbutton_view_p | ActionButton | widget_view_buttons | sizePolicy=0 0; minimumSize=50 40; maximumSize=50 40; baseSize=60 40; toolTip=Set view P; text=P; checkable=true; checked=true; autoExclusive=true; view_change_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| actionbutton_view_x | ActionButton | widget_view_buttons | sizePolicy=0 0; minimumSize=50 40; maximumSize=50 40; baseSize=60 40; toolTip=Set view X; text=X; checkable=true; autoExclusive=true; view_change_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=X; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| actionbutton_view_y | ActionButton | widget_view_buttons | sizePolicy=0 0; minimumSize=50 40; maximumSize=50 40; baseSize=60 40; toolTip=Set view Y; text=Y; checkable=true; autoExclusive=true; view_change_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=Y; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| actionbutton_view_z | ActionButton | widget_view_buttons | sizePolicy=0 0; minimumSize=50 40; maximumSize=50 40; baseSize=60 40; toolTip=Set view Z; text=Z; checkable=true; autoExclusive=true; view_change_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=Z; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| btn_dimensions | QPushButton | widget_view_buttons | sizePolicy=0 0; minimumSize=50 40; maximumSize=50 40; toolTip=Toggle display dimensions; text=D; checkable=true |
| actionbutton_zoom_in | ActionButton | widget_view_buttons | sizePolicy=0 0; minimumSize=50 40; maximumSize=50 40; baseSize=60 40; toolTip=Zoom in; text=+; checkable=false; autoRepeat=true; view_change_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=zoom-in; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| actionbutton_zoom_out | ActionButton | widget_view_buttons | sizePolicy=0 0; minimumSize=50 40; maximumSize=50 40; baseSize=60 40; toolTip=Zoom out; text=-; checkable=false; autoRepeat=true; view_change_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=zoom-out; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| actionbutton_clear | ActionButton | widget_view_buttons | sizePolicy=0 0; minimumSize=50 40; maximumSize=50 40; baseSize=60 40; toolTip=Clear display; autoFillBackground=false; text=C; checkable=false; estop_action=false; view_change_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=Clear; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| gcodegraphics | GCodeGraphics | stackedWidget_mainTabPage1 | sizePolicy=0 0; minimumSize=0 0; maximumSize=16777215 16777215; styleSheet=; _view=p; _dtg=false; background_color=100 100 100; _use_gradient_background=true; overlay=false |
| stackedWidget_mainTabPage2 | QWidget | stackedWidget_mainTab |  |
| widget_file_copy | QWidget | stackedWidget_mainTabPage2 |  |
| btn_load_file | QPushButton | widget_file_copy | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; toolTip=Load selected file; text=LOAD FILE |
| btn_copy_right | QPushButton | widget_file_copy | sizePolicy=0 0; minimumSize=80 60; maximumSize=80 60; toolTip=Copy file from left to right; text=; icon=:/buttons/images/Right_arrow.png:/buttons/images/Right_arrow.png; iconSize=60 60 |
| btn_copy_left | QPushButton | widget_file_copy | sizePolicy=0 0; minimumSize=80 60; maximumSize=80 60; toolTip=Copy file from right to left; text=; icon=:/buttons/images/Left_arrow.png:/buttons/images/Left_arrow.png; iconSize=60 60 |
| btn_gcode_edit | QPushButton | stackedWidget_mainTabPage2 | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; toolTip=Edit currently loaded gcode file; text=EDIT GCODE; checkable=true |
| filemanager | FileManager | stackedWidget_mainTabPage2 |  |
| gcode_editor | GcodeEditor | stackedWidget_mainTabPage2 | auto_show_mdi_status=false; auto_show_manual_status=false |
| stackedWidget_mainTabPage3 | QWidget | stackedWidget_mainTab |  |
| widget_offsets | QWidget | stackedWidget_mainTabPage3 |  |
| offset_table | OriginOffsetView | widget_offsets | enabled=true; frameShape=QFrame::NoFrame; autoScrollMargin=16; alternatingRowColors=false; selectionBehavior=QAbstractItemView::SelectItems; cornerButtonEnabled=false; horizontalHeaderMinimumSectionSize=80; horizontalHeaderDefaultSectionSize=80; verticalHeaderCascadingSectionResizes=false; verticalHeaderMinimumSectionSize=30; verticalHeaderDefaultSectionSize=30 |
| widget_zero_offsets | QWidget | stackedWidget_mainTabPage3 |  |
| action_zero_rotation | ActionButton | widget_zero_offsets | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; text=ZERO ROTATION; zero_zrot_action=true |
| action_zero_g92 | ActionButton | widget_zero_offsets | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; text=ZERO G92; zero_g92_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| action_zero_g5x | ActionButton | widget_zero_offsets | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; text=ZERO G5X; zero_g5x_action=true |
| stackedWidget_mainTabPage4 | QWidget | stackedWidget_mainTab |  |
| tooloffsetview | ToolOffsetView | stackedWidget_mainTabPage4 | enabled=true; autoFillBackground=false; frameShape=QFrame::NoFrame; alternatingRowColors=false; cornerButtonEnabled=true; horizontalHeaderDefaultSectionSize=60; horizontalHeaderHighlightSections=false; verticalHeaderVisible=false; verticalHeaderDefaultSectionSize=24; verticalHeaderHighlightSections=false |
| stackedWidget_mainTabPage5 | QWidget | stackedWidget_mainTab |  |
| stackedWidget_log | QStackedWidget | stackedWidget_mainTabPage5 | frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; currentIndex=0 |
| page_machine | QWidget | stackedWidget_log |  |
| machinelog | MachineLog | page_machine | sizePolicy=0 0; frameShape=QFrame::NoFrame; frameShadow=QFrame::Plain; documentTitle=Machine Log; readOnly=true; placeholderText=Machine Log |
| page_integrator | QWidget | stackedWidget_log |  |
| integrator_log | MachineLog | page_integrator | sizePolicy=0 0; frameShape=QFrame::NoFrame; frameShadow=QFrame::Plain; documentTitle=Integrator Log; readOnly=true; placeholderText=Integrator Log; integrator_log_option=true |
| widget_status_log | QWidget | stackedWidget_mainTabPage5 |  |
| btn_select_log | IndicatedPushButton | widget_status_log | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; checkable=true; checked=false; indicator_option=false; checked_state_text_option=true; python_command_option=true; on_color=0 255 0; true_state_string=SYSTEM LOG; false_state_string=MACHINE LOG; true_python_cmd_string=INSTANCE.stackedWidget_log.setCurrentIndex(1); false_python_cmd_string=INSTANCE.stackedWidget_log.setCurrentIndex(0) |
| btn_clear_status | QPushButton | widget_status_log | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; text=CLEAR STATUS |
| btn_save_status | QPushButton | widget_status_log | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; toolTip=Save status to file; text=SAVE TO FILE |
| btn_select_log_2 | IndicatedPushButton | widget_status_log | sizePolicy=0 0; minimumSize=80 50; maximumSize=80 50; text=Recall Error; checkable=false; checked=false; indicator_option=false; checked_state_text_option=false; python_command_option=true; on_color=0 255 0; true_state_string=SYSTEM LOG; false_state_string=MACHINE LOG; true_python_cmd_string=INSTANCE._NOTICE.show_last(); false_python_cmd_string= |
| stackedWidget_mainTabPage6 | QWidget | stackedWidget_mainTab |  |
| stackedWidget_mainTabPage7 | QWidget | stackedWidget_mainTab |  |
| camview | CamView | stackedWidget_mainTabPage7 |  |
| widget_cam_controls | QWidget | stackedWidget_mainTabPage7 | sizePolicy=0 0 |
| label_66 | QLabel | widget_cam_controls | maximumSize=16777215 20; text=ZOOM; alignment=Qt::AlignCenter |
| cam_zoom | QSlider | widget_cam_controls | sizePolicy=0 0; minimumSize=30 80; maximumSize=30 16777215; minimum=10; maximum=50; orientation=Qt::Vertical |
| label_64 | QLabel | widget_cam_controls | maximumSize=16777215 20; text=DIA; alignment=Qt::AlignCenter |
| cam_diameter | QSlider | widget_cam_controls | sizePolicy=0 0; minimumSize=30 80; maximumSize=30 16777215; minimum=20; maximum=100; singleStep=2; orientation=Qt::Vertical |
| label_65 | QLabel | widget_cam_controls | maximumSize=16777215 20; text=ROT; alignment=Qt::AlignCenter |
| cam_rotate | QSlider | widget_cam_controls | sizePolicy=0 0; minimumSize=30 80; maximumSize=30 16777215; maximum=900; orientation=Qt::Vertical |
| actionbutton | ActionButton | widget_cam_controls | minimumSize=0 42; toolTip=save Image to user/linuxcnc/nc_files/camImage.png; text=Save; python_command_option=true; true_python_cmd_string=INSTANCE.camview.saveImage(); false_python_cmd_string=; command_text_string= |
| stackedWidget_mainTabPage8 | QWidget | stackedWidget_mainTab |  |
| gcode_list | QListWidget | stackedWidget_mainTabPage8 | frameShape=QFrame::Box; frameShadow=QFrame::Raised; selectionMode=QAbstractItemView::SingleSelection |
| gcode_parameters | QLineEdit | stackedWidget_mainTabPage8 | sizePolicy=0 0; minimumSize=0 30; baseSize=0 30; readOnly=true; placeholderText=Parameters |
| gcode_description | QPlainTextEdit | stackedWidget_mainTabPage8 | frameShape=QFrame::Box; frameShadow=QFrame::Raised |
| stackedWidget_mainTabPage9 | QWidget | stackedWidget_mainTab |  |
| tabWidget_setup | QTabWidget | stackedWidget_mainTabPage9 | sizePolicy=0 0; styleSheet=QTabBar::tab{ min-height:36px; min-width:80px; }; currentIndex=0 |
| tabHTML | QWidget | tabWidget_setup | title=HTML |
| webwidget | WebWidget | tabHTML |  |
| tabPDF | QWidget | tabWidget_setup | title=PDF |
| tabProperties | QWidget | tabWidget_setup | title=PROPERTIES |
| textedit_properties | QTextEdit | tabProperties |  |
| stackedWidget_mainTabPage10 | QWidget | stackedWidget_mainTab |  |
| frm_settings1 | QWidget | stackedWidget_mainTabPage10 | sizePolicy=0 0; minimumSize=180 0; maximumSize=260 16777215 |
| label_23 | QLabel | frm_settings1 | frameShape=QFrame::NoFrame; frameShadow=QFrame::Raised; text=KEYBOARD MAPPING; alignment=Qt::AlignCenter |
| label_29 | QLabel | frm_settings1 | text=ESC - Program Abort |
| label_30 | QLabel | frm_settings1 | text=F1 - ESTOP |
| label_31 | QLabel | frm_settings1 | text=F2 - Machine OFF |
| label_36 | QLabel | frm_settings1 | text=F11 - Fullscreen |
| label_35 | QLabel | frm_settings1 | text=F12 - Style Sheet Editor |
| label_34 | QLabel | frm_settings1 | text=Home - HOME All |
| label_20 | QLabel | frm_settings1 | text=Pause - Pause program |
| chk_alpha_mode | QCheckBox | frm_settings1 | sizePolicy=0 0; toolTip=Make complicated 3D files more visible; text=ENABLE ALPHA MODE |
| chk_inhibit_selection | QCheckBox | frm_settings1 | sizePolicy=0 0; toolTip=Make complicated 3D files more visible; text=INHIBIT MOUSE SELECTION |
| chk_eoffsets | QCheckBox | frm_settings1 | sizePolicy=0 0; toolTip=Enable external offsets for spindle pause; text=USE EXTERNAL OFFSETS |
| chk_reload_tool | QCheckBox | frm_settings1 | sizePolicy=0 0; toolTip=Reload last loaded tool; text=RELOAD LAST TOOL |
| chk_reload_program | QCheckBox | frm_settings1 | sizePolicy=0 0; toolTip=Reload last loaded program; text=RELOAD LAST PROGRAM |
| chk_use_keyboard | QCheckBox | frm_settings1 | sizePolicy=0 0; toolTip=Enable keyboard shortcuts; text=USE KEYBOARD SHORTCUTS |
| chk_run_from_line | QCheckBox | frm_settings1 | sizePolicy=0 0; toolTip=Enable run from line; text=USE RUN FROM LINE |
| chk_use_virtual | QCheckBox | frm_settings1 | sizePolicy=0 0; toolTip=Enable use of onboard virtual keyboard; text=USE VIRTUAL KEYBOARD |
| chk_use_tool_sensor | QCheckBox | frm_settings1 | sizePolicy=0 0; toolTip=Enable tool sensor; text=USE TOOL SENSOR; checked=true |
| chk_use_camera | QCheckBox | frm_settings1 | sizePolicy=0 0; toolTip=Enable Webcam for work offset location; text=USE CAMERA; checked=true |
| chk_override_limits | QCheckBox | frm_settings1 | sizePolicy=0 0; text=OVERRIDE LIMITS |
| line | Line | stackedWidget_mainTabPage10 | orientation=Qt::Vertical |
| frm_settings2 | QWidget | stackedWidget_mainTabPage10 | sizePolicy=0 0; minimumSize=300 0; maximumSize=16777215 16777215 |
| widget_home_header | QWidget | frm_settings2 |  |
| label_61 | QLabel | widget_home_header | sizePolicy=0 0; minimumSize=120 30; maximumSize=120 30; text= |
| label_38 | QLabel | widget_home_header | sizePolicy=0 0; minimumSize=50 30; maximumSize=50 30; text=X; alignment=Qt::AlignCenter |
| label_39 | QLabel | widget_home_header | sizePolicy=0 0; minimumSize=50 30; maximumSize=50 30; text=Y; alignment=Qt::AlignCenter |
| widget_home_location | QWidget | frm_settings2 |  |
| label_26 | QLabel | widget_home_location | sizePolicy=0 0; minimumSize=120 30; maximumSize=120 30; text=HOME LOCATION |
| lbl_home_x | QLineEdit | widget_home_location | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; maxLength=8; alignment=Qt::AlignCenter; readOnly=true |
| lbl_home_y | QLineEdit | widget_home_location | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; maxLength=8; alignment=Qt::AlignCenter; readOnly=true |
| groupBox_probe_parameters | QGroupBox | frm_settings2 | title=TOUCHOFF PARAMETERS; alignment=Qt::AlignCenter |
| widget_search_vel | QWidget | groupBox_probe_parameters | minimumSize=0 30; maximumSize=16777215 30 |
| label_6 | QLabel | widget_search_vel | sizePolicy=0 0; minimumSize=120 0; maximumSize=120 16777215; toolTip=Probe down search velocity; text=SEARCH VELOCITY; alignment=Qt::AlignLeading&#124;Qt::AlignLeft&#124;Qt::AlignVCenter |
| lineEdit_search_vel | QLineEdit | widget_search_vel | sizePolicy=0 0; minimumSize=60 0; maximumSize=60 16777215; maxLength=8; alignment=Qt::AlignCenter; readOnly=false |
| lbl_search_vel_units | QLabel | widget_search_vel | sizePolicy=0 0; minimumSize=60 0; maximumSize=60 16777215; text=MM/MIN; alignment=Qt::AlignCenter; wordWrap=false; indent=0 |
| widget_probe_vel | QWidget | groupBox_probe_parameters | minimumSize=0 30; maximumSize=16777215 30 |
| label_7 | QLabel | widget_probe_vel | sizePolicy=0 0; minimumSize=120 0; maximumSize=120 16777215; toolTip=Probe down final velocity; text=PROBE VELOCITY; alignment=Qt::AlignLeading&#124;Qt::AlignLeft&#124;Qt::AlignVCenter |
| lineEdit_probe_vel | QLineEdit | widget_probe_vel | sizePolicy=0 0; minimumSize=60 0; maximumSize=60 16777215; maxLength=8; alignment=Qt::AlignCenter; readOnly=false |
| lbl_probe_vel_units | QLabel | widget_probe_vel | sizePolicy=0 0; minimumSize=60 0; maximumSize=60 16777215; text=MM/MIN; alignment=Qt::AlignCenter; wordWrap=false; indent=0 |
| widget_max_probe | QWidget | groupBox_probe_parameters | minimumSize=0 30; maximumSize=16777215 30 |
| label_4 | QLabel | widget_max_probe | sizePolicy=0 0; minimumSize=120 0; maximumSize=120 16777215; toolTip=Max probing distance; text=MAX PROBE; alignment=Qt::AlignLeading&#124;Qt::AlignLeft&#124;Qt::AlignVCenter |
| lineEdit_max_probe | QLineEdit | widget_max_probe | sizePolicy=0 0; minimumSize=60 0; maximumSize=60 16777215; maxLength=8; alignment=Qt::AlignCenter; readOnly=false |
| lbl_max_probe_units | QLabel | widget_max_probe | sizePolicy=0 0; minimumSize=60 0; maximumSize=60 16777215; text=MM; alignment=Qt::AlignCenter; wordWrap=false; indent=0 |
| widget_return_dist | QWidget | groupBox_probe_parameters | minimumSize=0 30; maximumSize=16777215 30 |
| label_52 | QLabel | widget_return_dist | sizePolicy=0 0; minimumSize=120 0; maximumSize=120 16777215; toolTip=Distance to retract after G38.2 command; text=RETRACT DISTANCE |
| lineEdit_retract_distance | QLineEdit | widget_return_dist | sizePolicy=0 0; minimumSize=60 0; maximumSize=60 16777215; maxLength=8; alignment=Qt::AlignCenter |
| lbl_retract_dist_units | QLabel | widget_return_dist | sizePolicy=0 0; minimumSize=60 0; maximumSize=60 16777215; text=MM; alignment=Qt::AlignCenter |
| widget_z_safe_travel | QWidget | groupBox_probe_parameters | minimumSize=0 30; maximumSize=16777215 30 |
| label_53 | QLabel | widget_z_safe_travel | sizePolicy=0 0; minimumSize=120 0; maximumSize=120 16777215; toolTip=Z safe travel height during rapid moves; text=Z SAFE TRAVEL |
| lineEdit_z_safe_travel | QLineEdit | widget_z_safe_travel | sizePolicy=0 0; minimumSize=60 0; maximumSize=60 16777215; maxLength=8; alignment=Qt::AlignCenter |
| lbl_z_safe_travel_units | QLabel | widget_z_safe_travel | sizePolicy=0 0; minimumSize=60 0; maximumSize=60 16777215; text=MM; alignment=Qt::AlignCenter |
| groupBox | QGroupBox | frm_settings2 | title=SPINDLE RAISE; alignment=Qt::AlignCenter |
| widget_ext_offset | QWidget | groupBox |  |
| pushbutton_6 | PushButton | widget_ext_offset | minimumSize=50 30; maximumSize=50 30; text=+ |
| pushbutton_7 | PushButton | widget_ext_offset | minimumSize=50 30; maximumSize=50 30; text=- |
| lineEdit_eoffset_count | QLineEdit | widget_ext_offset | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; maxLength=8; alignment=Qt::AlignCenter; readOnly=false |
| lbl_z_ext_offset | QLabel | widget_ext_offset | sizePolicy=0 0; minimumSize=60 30; maximumSize=60 30; text=MM; alignment=Qt::AlignCenter |
| groupBox_gcode_zoom | QGroupBox | frm_settings2 | title=GCODE ZOOM; alignment=Qt::AlignCenter |
| pushbutton_5 | PushButton | groupBox_gcode_zoom | minimumSize=50 30; maximumSize=50 30; text=+ |
| pushbutton_4 | PushButton | groupBox_gcode_zoom | minimumSize=50 30; maximumSize=50 30; text=- |
| silver_dragon | QLabel | frm_settings2 | minimumSize=0 1; sizeIncrement=0 0; text=; pixmap=:/images/images/silver_dragon.png |
| line_2 | Line | stackedWidget_mainTabPage10 | orientation=Qt::Vertical |
| widget_settings3 | QWidget | stackedWidget_mainTabPage10 | sizePolicy=0 0; minimumSize=100 0 |
| pushbutton_3 | QToolButton | widget_settings3 | minimumSize=96 46; maximumSize=96 50; text=ABOUT |
| pushbutton_2 | PushButton | widget_settings3 | minimumSize=96 46; maximumSize=96 50; text=TEST BUTTON; python_command_option=true; true_python_cmd_string=PROGRAM_LOADER.load_test_button(); false_python_cmd_string= |
| pushbutton | PushButton | widget_settings3 | minimumSize=96 46; maximumSize=96 50; text=TEST LED; python_command_option=true; true_python_cmd_string=PROGRAM_LOADER.load_test_led(); false_python_cmd_string= |
| actionbutton_lcnc_status_3 | ActionButton | widget_settings3 | sizePolicy=0 0; minimumSize=96 46; maximumSize=96 50; text=CALIBRATION; indicator_option=false; indicator_HAL_pin_option=false; indicator_status_option=false; checked_state_text_option=false; python_command_option=false; on_color=255 0 0; shape_option=0; off_color=0 0 0; indicator_size=0.300000000000000; circle_diameter=10; right_edge_offset=0; top_edge_offset=0; corner_radius=5.000000000000000; height_fraction=0.300000000000000; width_fraction=0.900000000000000; true_state_string=True; false_state_string=False; true_python_cmd_string=print"true command"; false_python_cmd_string=print"false command"; invert_the_status=false; is_paused_status=false; is_estopped_status=false; is_on_status=false; is_idle_status=false; is_homed_status=false; is_flood_status=false; is_mist_status=false; is_block_delete_status=false; is_optional_stop_status=false; is_joint_homed_status=false; is_limits_overridden_status=false; is_manual_status=false; is_mdi_status=false; is_auto_status=false; is_spindle_stopped_status=false; is_spindle_fwd_status=false; is_spindle_rev_status=false; joint_number_status=0; launch_status_action=false; launch_calibration_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=0.300000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm; actionName=tool.status |
| actionbutton_lcnc_status | ActionButton | widget_settings3 | sizePolicy=0 0; minimumSize=96 46; maximumSize=96 50; text=STATUS; launch_status_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm; actionName=tool.status |
| actionbutton_halscope | ActionButton | widget_settings3 | sizePolicy=0 0; minimumSize=96 46; maximumSize=96 50; text=HAL SCOPE; launch_halscope_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm; actionName=tool.halscope |
| actionbutton_halmeter | ActionButton | widget_settings3 | sizePolicy=0 0; minimumSize=96 46; maximumSize=96 50; text=HAL METER; launch_halmeter_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm; actionName=tool.halmeter |
| actionbutton_halshow | ActionButton | widget_settings3 | sizePolicy=0 0; minimumSize=96 46; maximumSize=96 50; text=HAL SHOW; launch_halshow_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm; actionName=tool.halshow |
| main_tab_Page_Utilities | QWidget | stackedWidget_mainTab |  |
| tabWidget_utilities | QTabWidget | main_tab_Page_Utilities | currentIndex=0 |
| facing | QWidget | tabWidget_utilities | title=FACING |
| hole_circle | QWidget | tabWidget_utilities | title=Bolt Hole Circle |
| ngcgui | QWidget | tabWidget_utilities | title=NgcGui |
| frame_macro_buttons | QWidget | frm_backplot | enabled=true; sizePolicy=0 0; minimumSize=74 0; maximumSize=74 16777215 |
| macrobutton0 | ActionButton | frame_macro_buttons | enabled=true; sizePolicy=0 0; minimumSize=70 35; maximumSize=70 54; baseSize=70 45; toolTip=Run Macro 0; layoutDirection=Qt::LeftToRight; text=Macro0; checkable=false; autoExclusive=false; view_change_action=false; ini_mdi_command_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=p; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| macrobutton1 | ActionButton | frame_macro_buttons | enabled=true; sizePolicy=0 0; minimumSize=70 35; maximumSize=70 54; baseSize=70 45; focusPolicy=Qt::StrongFocus; toolTip=Run Macro 1; text=Macro1; checkable=false; autoExclusive=false; view_change_action=false; ini_mdi_command_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=p; command_text_string=; ini_mdi_number=1; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| macrobutton2 | ActionButton | frame_macro_buttons | enabled=true; sizePolicy=0 0; minimumSize=70 35; maximumSize=70 54; baseSize=70 45; toolTip=Run Macro 2; text=Macro2; checkable=false; autoExclusive=false; view_change_action=false; ini_mdi_command_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=p; command_text_string=; ini_mdi_number=2; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| macrobutton3 | ActionButton | frame_macro_buttons | enabled=true; sizePolicy=0 0; minimumSize=70 35; maximumSize=70 54; baseSize=70 45; toolTip=Run Macro 3; text=Macro3; checkable=false; autoExclusive=false; view_change_action=false; ini_mdi_command_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=p; command_text_string=; ini_mdi_number=3; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| macrobutton4 | ActionButton | frame_macro_buttons | enabled=true; sizePolicy=0 0; minimumSize=70 35; maximumSize=70 54; baseSize=70 45; toolTip=Run Macro 4; text=Macro4; checkable=false; autoExclusive=false; view_change_action=false; ini_mdi_command_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=p; command_text_string=; ini_mdi_number=4; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| macrobutton5 | ActionButton | frame_macro_buttons | enabled=true; sizePolicy=0 0; minimumSize=70 35; maximumSize=70 54; baseSize=70 45; toolTip=Run Macro 5; text=Macro5; checkable=false; autoExclusive=false; view_change_action=false; ini_mdi_command_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=p; command_text_string=; ini_mdi_number=5; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| macrobutton6 | ActionButton | frame_macro_buttons | enabled=true; sizePolicy=0 0; minimumSize=70 35; maximumSize=70 54; baseSize=70 45; toolTip=Run Macro 6; text=Macro6; checkable=false; autoRepeat=false; autoRepeatDelay=300; autoRepeatInterval=100; view_change_action=false; ini_mdi_command_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=p; command_text_string=; ini_mdi_number=6; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| macrobutton7 | ActionButton | frame_macro_buttons | enabled=true; sizePolicy=0 0; minimumSize=70 35; maximumSize=70 54; baseSize=70 45; toolTip=Run Macro 7; text=Macro7; checkable=false; autoRepeat=false; autoRepeatDelay=300; autoRepeatInterval=100; view_change_action=false; ini_mdi_command_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=p; command_text_string=; ini_mdi_number=7; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| macrobutton8 | ActionButton | frame_macro_buttons | enabled=true; sizePolicy=0 0; minimumSize=70 35; maximumSize=70 54; baseSize=70 45; toolTip=Run Macro 8; autoFillBackground=false; text=Macro8; checkable=false; view_change_action=false; ini_mdi_command_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=p; command_text_string=; ini_mdi_number=8; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| macrobutton9 | ActionButton | frame_macro_buttons | enabled=true; sizePolicy=0 0; minimumSize=70 35; maximumSize=70 54; baseSize=70 45; toolTip=Run Macro 9; autoFillBackground=false; text=Macro9; checkable=false; view_change_action=false; ini_mdi_command_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=p; command_text_string=; ini_mdi_number=9; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| jogging_frame | QFrame | widget_graphics | sizePolicy=0 0; minimumSize=268 0; maximumSize=300 16777215; frameShape=QFrame::Box; frameShadow=QFrame::Raised; lineWidth=1 |
| widget_jog_control | QWidget | jogging_frame |  |
| widget_jog_buttons | QWidget | widget_jog_control | minimumSize=0 0 |
| plus_jogbutton_4 | ActionButton | widget_jog_buttons | minimumSize=53 53; maximumSize=53 53; styleSheet=; text=; iconSize=44 44; jog_joint_pos_action=true; joint_number=-1; axis_letter=A |
| y_minus_jogbutton | ActionButton | widget_jog_buttons | sizePolicy=0 0; minimumSize=53 53; maximumSize=53 53; text=; icon=:/buttons/images/y_minus_jog_button.png:/buttons/images/y_minus_jog_button.png; iconSize=44 44; jog_joint_neg_action=true; template_label_option=false; joint_number=-1; axis_letter=Y; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| z_plus_jogbutton | ActionButton | widget_jog_buttons | sizePolicy=0 0; minimumSize=53 53; maximumSize=53 53; text=; icon=:/buttons/images/z_plus_jog_button.png:/buttons/images/z_plus_jog_button.png; iconSize=44 44; jog_joint_pos_action=true; joint_number=-1; axis_letter=Z |
| x_minus_jogbutton | ActionButton | widget_jog_buttons | sizePolicy=0 0; minimumSize=53 53; maximumSize=53 53; text=; icon=:/buttons/images/x_minus_jog_button.png:/buttons/images/x_minus_jog_button.png; iconSize=44 44; jog_joint_neg_action=true; template_label_option=false; joint_number=-1; axis_letter=X; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| x_plus_jogbutton | ActionButton | widget_jog_buttons | sizePolicy=0 0; minimumSize=53 53; maximumSize=53 53; text=; icon=:/buttons/images/x_plus_jog_button.png:/buttons/images/x_plus_jog_button.png; iconSize=44 44; jog_joint_pos_action=true; template_label_option=false; joint_number=-1; axis_letter=X; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| minus_jogbutton_4 | ActionButton | widget_jog_buttons | minimumSize=53 53; maximumSize=53 53; text=; iconSize=44 44; jog_joint_pos_action=false; jog_joint_neg_action=true; joint_number=-1; axis_letter=A |
| z_minus_jogbutton | ActionButton | widget_jog_buttons | minimumSize=53 53; maximumSize=53 53; text=; icon=:/buttons/images/z_minus_jog_button.png:/buttons/images/z_minus_jog_button.png; iconSize=44 44; jog_joint_neg_action=true; joint_number=-1; axis_letter=Z |
| y_plus_jogbutton | ActionButton | widget_jog_buttons | minimumSize=53 53; maximumSize=53 53; text=; icon=:/buttons/images/y_plus_jog_button.png:/buttons/images/y_plus_jog_button.png; iconSize=44 44; jog_joint_pos_action=true; template_label_option=false; joint_number=-1; axis_letter=Y; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| plus_jogbutton_5 | ActionButton | widget_jog_buttons | minimumSize=53 53; maximumSize=53 53; text=; iconSize=44 44; jog_joint_pos_action=true; joint_number=-1; axis_letter=C |
| minus_jogbutton_5 | ActionButton | widget_jog_buttons | minimumSize=53 53; maximumSize=53 53; styleSheet=; text=; iconSize=44 44; jog_joint_pos_action=false; jog_joint_neg_action=true; joint_number=-1; axis_letter=C |
| widget_jograte | QWidget | widget_jog_control | sizePolicy=0 0; minimumSize=70 0; maximumSize=80 16777215 |
| label_19 | QLabel | widget_jograte | sizePolicy=0 0; minimumSize=50 20; maximumSize=58 20; text=UNITS; alignment=Qt::AlignCenter |
| statelabel_metric | StateLabel | widget_jograte | sizePolicy=0 0; minimumSize=56 24; maximumSize=58 24; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; scaledContents=false; alignment=Qt::AlignCenter; css_mode_status=false; fpr_mode_status=false; true_textTemplate=MM; false_textTemplate=IN |
| lbl_jog_linear | QLabel | widget_jograte | sizePolicy=0 0; minimumSize=0 30; maximumSize=58 30; text=JOG RATE MM/MIN; alignment=Qt::AlignCenter |
| status_jog_linear | StatusLabel | widget_jograte | sizePolicy=0 0; minimumSize=56 28; maximumSize=58 28; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; alignment=Qt::AlignCenter; textTemplate=%.1f; alt_textTemplate=%d; jograte_status=true |
| slider_jog_linear | StatusSlider | widget_jograte | sizePolicy=0 0; minimumSize=30 122; maximumSize=30 16777215; toolTip=Adjust linear jog rate; maximum=3600; singleStep=100; pageStep=100; value=3000; orientation=Qt::Vertical; pin_name=slider-jogspeed-linear; jograte_rate=true |
| btn_jog_l_slow | IndicatedPushButton | widget_jograte | sizePolicy=0 0; minimumSize=50 30; maximumSize=50 30; toolTip=Toggle linear jog speed range; text=FAST; checkable=true; checked_state_text_option=true; true_state_string=SLOW; false_state_string=FAST; slider=slider_jog_linear |
| widget_increments_linear | QWidget | jogging_frame | sizePolicy=0 0 |
| lbl_increments_linear | QLabel | widget_increments_linear | sizePolicy=0 0; minimumSize=0 25; maximumSize=150 30; text=LINEAR INCREMENT; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; indent=2 |
| jogincrements_linear | JogIncrements | widget_increments_linear | sizePolicy=0 0; minimumSize=80 25; maximumSize=100 25; sizeIncrement=0 0; focusPolicy=Qt::ClickFocus; toolTip=Select jog increment; toolTipDuration=12; maxVisibleItems=20; maxCount=20; frame=true |
| widget_increments_angular | QWidget | jogging_frame | sizePolicy=0 0 |
| lbl_increments_angular | QLabel | widget_increments_angular | sizePolicy=0 0; minimumSize=0 25; maximumSize=150 30; text=ANGULAR INCREMENT; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; margin=0; indent=2 |
| jogincrements_angular | JogIncrements | widget_increments_angular | sizePolicy=0 0; minimumSize=80 25; maximumSize=100 25; sizeIncrement=0 0; focusPolicy=Qt::ClickFocus; toolTip=Select jog increment; currentIndex=-1; maxVisibleItems=20; maxCount=20; linear_option=false |
| widget_jog_angular | QWidget | jogging_frame | sizePolicy=0 0; minimumSize=0 32 |
| lbl_jog_angular | QLabel | widget_jog_angular | sizePolicy=0 0; minimumSize=0 26; maximumSize=20 28; font=12; text=A; alignment=Qt::AlignCenter |
| btn_jog_a_slow | IndicatedPushButton | widget_jog_angular | sizePolicy=0 0; minimumSize=50 26; maximumSize=50 28; toolTip=Toggle angular jog speed range; text=FAST; checkable=true; checked_state_text_option=true; true_state_string=SLOW; false_state_string=FAST; slider=slider_jog_angular |
| slider_jog_angular | StatusSlider | widget_jog_angular | sizePolicy=0 0; minimumSize=0 26; maximumSize=16777215 28; toolTip=Adjust angular jog rate; maximum=3600; singleStep=100; pageStep=100; value=3000; orientation=Qt::Horizontal; pin_name=slider-jogspeed-angular; jograte_rate=false; jograte_angular_rate=true |
| status_jog_angular | StatusLabel | widget_jog_angular | sizePolicy=0 0; minimumSize=54 26; maximumSize=54 28; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; alignment=Qt::AlignCenter; textTemplate=%d; jograte_status=false; jograte_angular_status=true |
| widget_program_tool | QWidget | screen_options | sizePolicy=0 0; minimumSize=0 0; maximumSize=421 354 |
| frame_program | QFrame | widget_program_tool | sizePolicy=0 0; minimumSize=195 0; frameShape=QFrame::Box; frameShadow=QFrame::Raised |
| btn_start | IndicatedPushButton | frame_program | sizePolicy=0 0; minimumSize=86 39; maximumSize=120 64; text=CYCLE START; indicator_option=true; indicator_status_option=true; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=6; top_edge_offset=6; invert_the_status=true; is_idle_status=true |
| action_abort | ActionButton | frame_program | sizePolicy=0 0; minimumSize=86 39; maximumSize=120 64; text=STOP; python_command_option=true; true_python_cmd_string=INSTANCE.progressBar.setFormat('STOPPED'); false_python_cmd_string=; abort_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| action_pause | ActionButton | frame_program | sizePolicy=0 0; minimumSize=86 39; maximumSize=120 64; text=PAUSE; checkable=true; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=true; on_color=255 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=6; top_edge_offset=6; true_state_string=RESUME; false_state_string=PAUSE; is_paused_status=true; pause_action=true |
| action_step | ActionButton | frame_program | sizePolicy=0 0; minimumSize=86 39; maximumSize=120 64; text=STEP; step_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| action_opt_blk | ActionButton | frame_program | sizePolicy=0 0; minimumSize=86 39; maximumSize=120 64; text=OPT BLOCK; checkable=true; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; circle_diameter=10; right_edge_offset=6; top_edge_offset=6; is_block_delete_status=true; block_delete_action=true |
| action_opt_stp | ActionButton | frame_program | sizePolicy=0 0; minimumSize=86 39; maximumSize=120 64; text=OPT STOP; checkable=true; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=6; top_edge_offset=6; is_optional_stop_status=true; optional_stop_action=true |
| action_mist | ActionButton | frame_program | sizePolicy=0 0; minimumSize=86 39; maximumSize=120 64; text=MIST OFF; checkable=true; checked=false; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=true; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=6; top_edge_offset=6; true_state_string=MIST ON; false_state_string=MIST OFF; is_mist_status=true; mist_action=true |
| action_flood | ActionButton | frame_program | sizePolicy=0 0; minimumSize=86 39; maximumSize=120 64; text=FLOOD OFF; checkable=true; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=true; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=6; top_edge_offset=6; true_state_string=FLOOD ON; false_state_string=FLOOD OFF; is_flood_status=true; flood_action=true |
| btn_reload_file | QPushButton | frame_program | sizePolicy=0 0; minimumSize=86 39; maximumSize=120 64; toolTip=Reload last loaded program; text=RELOAD |
| btn_spindle_pause | IndicatedPushButton | frame_program | sizePolicy=0 0; minimumSize=86 39; maximumSize=120 64; toolTip=Spindle pause; text=PAUSE SPINDLE; checkable=true; checked=false; pin_name=; indicator_option=false; indicator_HAL_pin_option=false; checked_state_text_option=true; on_color=255 0 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=6; top_edge_offset=6; true_state_string=SPINDLE PAUSED; false_state_string=PAUSE SPINDLE; isAutoPauseSensitive=true |
| progressBar | QProgressBar | frame_program | sizePolicy=0 0; minimumSize=90 24; maximumSize=241 24; font=Lato 75 true; autoFillBackground=false; inputMethodHints=Qt::ImhNone; maximum=99; value=0; alignment=Qt::AlignCenter; textVisible=true; invertedAppearance=false |
| frame_tool | QFrame | widget_program_tool | sizePolicy=0 0; minimumSize=172 0; maximumSize=172 16777215; frameShape=QFrame::Box; frameShadow=QFrame::Raised |
| lbl_tool_image | QLabel | frame_tool | sizePolicy=0 0; minimumSize=20 0; text=; pixmap=:/images/images/atc_spindle_tool.png; scaledContents=false; alignment=Qt::AlignBottom&#124;Qt::AlignHCenter |
| widget_tool | QWidget | frame_tool |  |
| label_22 | QLabel | widget_tool | sizePolicy=0 0; minimumSize=20 20; maximumSize=60 20; text=TOOL; alignment=Qt::AlignCenter |
| label_24 | QLabel | widget_tool | sizePolicy=0 0; minimumSize=20 20; maximumSize=60 20; text=DIA; alignment=Qt::AlignCenter |
| label_32 | QLabel | widget_tool | sizePolicy=0 0; minimumSize=20 20; maximumSize=60 20; text=SCS; alignment=Qt::AlignCenter |
| status_tool_no | StatusLabel | widget_tool | sizePolicy=0 0; minimumSize=20 24; maximumSize=56 24; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; alignment=Qt::AlignCenter; tool_number_status=true |
| status_tool_diameter | StatusLabel | widget_tool | sizePolicy=0 0; minimumSize=62 24; maximumSize=83 24; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; text=200.000; alignment=Qt::AlignCenter; textTemplate=%5.3f; alt_textTemplate=%5.3f; index_number=0; tool_diameter_status=true |
| statuslabel_vc | StatusLabel | widget_tool | sizePolicy=0 0; minimumSize=20 24; maximumSize=56 24; toolTip=Surface cutting speed; statusTip=; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; text=200; alignment=Qt::AlignCenter; textTemplate=%d; alt_textTemplate=%d; feed_override_status=false; actual_surface_speed_status=true |
| tool_desc_status | StatusLabel | widget_tool | sizePolicy=0 0; minimumSize=20 26; maximumSize=179 26; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; text=No Tool Loaded; scaledContents=false; alignment=Qt::AlignCenter; tool_comment_status=true |
| stackedWidget_dro | QStackedWidget | screen_options | sizePolicy=0 0; minimumSize=0 220; maximumSize=1000 356; currentIndex=0 |
| page_dro | QWidget | stackedWidget_dro |  |
| widget_dro_ovr | QWidget | page_dro | sizePolicy=21 0; minimumSize=643 0; maximumSize=1210 354 |
| frame_dro | QFrame | widget_dro_ovr | sizePolicy=10 0; minimumSize=0 0; maximumSize=526 16777211; frameShape=QFrame::Box; frameShadow=QFrame::Raised; lineWidth=1 |
| widget_dro | QWidget | frame_dro |  |
| action_zero_y | ActionButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; toolTip=Zero axis Y; text=ZERO; indicator_option=false; indicator_HAL_pin_option=false; on_color=0 255 0; off_color=255 0 0; indicator_size=0.200000000000000; mdi_action=false; zero_axis_action=true; template_label_option=false; joint_number=1; axis_letter=Y; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| dro_button_stack_x | QStackedWidget | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; currentIndex=1 |
| page_5 | QWidget | dro_button_stack_x | sizePolicy=0 0; maximumSize=82 64 |
| btn_home_x | IndicatedPushButton | page_5 | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; text=HOME; iconSize=16 16; checkable=false; checked=false; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=false; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=4; top_edge_offset=5; true_state_string=UNHOME; false_state_string=HOME; is_homed_status=false; is_joint_homed_status=true; joint=0 |
| page_6 | QWidget | dro_button_stack_x | sizePolicy=0 0; minimumSize=58 40; maximumSize=82 64 |
| offsettoolbutton_x | OffsetToolButton | page_6 | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; sizeIncrement=0 0; baseSize=0 0; text=TOOL; iconSize=24 24; popupMode=QToolButton::InstantPopup; axis_letter=X |
| actionbutton_abs | ActionButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; baseSize=0 0; toolTip=Show absolute coordinates; text=ABS; checkable=true; checked=true; autoExclusive=true; dro_absolute_action=true |
| action_zero_4 | ActionButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; toolTip=Zero axis A; text=ZERO; indicator_option=false; indicator_HAL_pin_option=false; on_color=0 255 0; off_color=255 0 0; indicator_size=0.200000000000000; mdi_action=false; zero_axis_action=true; template_label_option=false; joint_number=3; axis_letter=A; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| dro_axis_x | DROLabel | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=16777215 64; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; Qjoint_number=0; homed=false |
| axistoolbutton_z | AxisToolButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; text=REF Z; popupMode=QToolButton::InstantPopup; arrowType=Qt::NoArrow; joint_number=2; axis_letter=Z; halpin_option=false; dialog_code_string=CALCULATOR |
| label_axis_5 | QLabel | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; frameShape=QFrame::WinPanel; frameShadow=QFrame::Raised; lineWidth=2; text=C; alignment=Qt::AlignCenter |
| actionbutton_rel | ActionButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; baseSize=0 0; toolTip=Show relative coordinates; text=G54; checkable=true; autoExclusive=true; dro_absolute_action=false; dro_relative_action=true |
| dro_button_stack_y | QStackedWidget | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; currentIndex=1 |
| page_7 | QWidget | dro_button_stack_y | sizePolicy=0 0; maximumSize=82 64 |
| btn_home_y | IndicatedPushButton | page_7 | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; text=HOME; iconSize=16 16; checkable=false; checked=false; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=false; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=4; top_edge_offset=5; true_state_string=UNHOME; false_state_string=HOME; is_homed_status=false; is_joint_homed_status=true; joint_number_status=1; joint=1 |
| page_8 | QWidget | dro_button_stack_y | sizePolicy=0 0; minimumSize=58 40; maximumSize=82 64 |
| offsettoolbutton_y | OffsetToolButton | page_8 | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; baseSize=0 0; text=TOOL; popupMode=QToolButton::InstantPopup; axis_letter=Y |
| axistoolbutton_y | AxisToolButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; text=REF Y; popupMode=QToolButton::InstantPopup; arrowType=Qt::NoArrow; joint_number=1; axis_letter=Y; halpin_option=false; dialog_code_string=CALCULATOR |
| dro_axis_4 | DROLabel | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=16777215 64; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; Qjoint_number=3; homed=false |
| dro_axis_5 | DROLabel | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=16777215 64; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; Qjoint_number=4; homed=false |
| actionbutton_dtg | ActionButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; baseSize=0 0; toolTip=Show distance to go; text=DTG; checkable=true; autoExclusive=true; dro_absolute_action=false; dro_dtg_action=true |
| label_axis_x | QLabel | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; frameShape=QFrame::WinPanel; frameShadow=QFrame::Raised; lineWidth=2; text=X; alignment=Qt::AlignCenter |
| btn_home_all | IndicatedPushButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=200 64; text=HOME ALL; indicator_option=true; indicator_status_option=true; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=4; top_edge_offset=5; is_homed_status=true |
| dro_axis_y | DROLabel | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=16777215 64; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; Qjoint_number=1; homed=false |
| action_zero_z | ActionButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; toolTip=Zero axis Z; text=ZERO; indicator_option=false; indicator_HAL_pin_option=false; on_color=0 255 0; off_color=255 0 0; indicator_size=0.200000000000000; mdi_action=false; zero_axis_action=true; template_label_option=false; joint_number=2; axis_letter=Z; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| dro_axis_z | DROLabel | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=16777215 64; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; Qjoint_number=2; homed=false |
| axistoolbutton_4 | AxisToolButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; text=REFA; popupMode=QToolButton::InstantPopup; arrowType=Qt::NoArrow; joint_number=3; axis_letter=A; halpin_option=false; dialog_code_string=CALCULATOR |
| label_axis_z | QLabel | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; frameShape=QFrame::WinPanel; frameShadow=QFrame::Raised; lineWidth=2; text=Z; alignment=Qt::AlignCenter |
| label_axis_y | QLabel | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; frameShape=QFrame::WinPanel; frameShadow=QFrame::Raised; lineWidth=2; text=Y; alignment=Qt::AlignCenter |
| axistoolbutton_5 | AxisToolButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; text=REFA; popupMode=QToolButton::InstantPopup; arrowType=Qt::NoArrow; joint_number=5; axis_letter=C; halpin_option=false; dialog_code_string=CALCULATOR |
| label_axis_4 | QLabel | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; frameShape=QFrame::WinPanel; frameShadow=QFrame::Raised; lineWidth=2; text=A; alignment=Qt::AlignCenter |
| action_zero_x | ActionButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; toolTip=Zero axis X; text=ZERO; indicator_option=false; indicator_HAL_pin_option=false; on_color=0 255 0; off_color=255 0 0; indicator_size=0.200000000000000; mdi_action=false; zero_axis_action=true; template_label_option=false; joint_number=0; axis_letter=X; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| axistoolbutton_x | AxisToolButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; text=REF X; popupMode=QToolButton::InstantPopup; arrowType=Qt::NoArrow; axis_letter=X; halpin_option=false; dialog_code_string=CALCULATOR |
| systemtoolbutton | SystemToolButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; toolTip=Select work coordinate system; text=WCS; popupMode=QToolButton::InstantPopup |
| dro_button_stack_z | QStackedWidget | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; currentIndex=1 |
| page_9 | QWidget | dro_button_stack_z | sizePolicy=0 0; maximumSize=82 64 |
| btn_home_z | IndicatedPushButton | page_9 | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; text=HOME; checkable=false; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=false; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=4; top_edge_offset=5; true_state_string=UNHOME; false_state_string=HOME; is_joint_homed_status=true; joint_number_status=2; joint=2 |
| page_10 | QWidget | dro_button_stack_z | sizePolicy=0 0; minimumSize=58 40; maximumSize=82 64 |
| offsettoolbutton_z | OffsetToolButton | page_10 | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; baseSize=0 0; text=TOOL; popupMode=QToolButton::InstantPopup; axis_letter=Z |
| action_zero_5 | ActionButton | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; toolTip=Zero axis A; text=ZERO; indicator_option=false; indicator_HAL_pin_option=false; on_color=0 255 0; off_color=255 0 0; indicator_size=0.200000000000000; mdi_action=false; zero_axis_action=true; template_label_option=false; joint_number=5; axis_letter=C; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| dro_button_stack_5 | QStackedWidget | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; currentIndex=1 |
| page_13 | QWidget | dro_button_stack_5 | sizePolicy=0 0; maximumSize=82 64 |
| action_home_5 | IndicatedPushButton | page_13 | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; text=HOME; checkable=false; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=false; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=4; top_edge_offset=5; true_state_string=UNHOME; false_state_string=HOME; is_joint_homed_status=true; joint_number_status=4; joint=4 |
| page_14 | QWidget | dro_button_stack_5 | sizePolicy=0 0; minimumSize=58 40; maximumSize=82 64 |
| offsettoolbutton_5 | OffsetToolButton | page_14 | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; baseSize=0 0; text=TOOL; popupMode=QToolButton::InstantPopup; axis_letter=A |
| page | QWidget | dro_button_stack_5 |  |
| action_home_7 | ActionButton | page | enabled=true; sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; focusPolicy=Qt::StrongFocus; text=GO TO ZERO; indicator_option=false; indicator_HAL_pin_option=false; on_color=0 255 0; off_color=255 0 0; indicator_size=0.200000000000000; mdi_action=false; home_action=false; mdi_command_action=true; template_label_option=false; joint_number=3; axis_letter=A; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=G90 G0 A0; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| dro_button_stack_4 | QStackedWidget | widget_dro | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; currentIndex=1 |
| page_2 | QWidget | dro_button_stack_4 |  |
| action_home_4 | IndicatedPushButton | page_2 | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; text=HOME; checkable=false; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=false; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=4; top_edge_offset=5; true_state_string=UNHOME; false_state_string=HOME; is_joint_homed_status=true; joint_number_status=3; joint=3 |
| page_12 | QWidget | dro_button_stack_4 | sizePolicy=0 0; minimumSize=58 40; maximumSize=82 64 |
| offsettoolbutton_4 | OffsetToolButton | page_12 | sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; baseSize=0 0; text=TOOL; popupMode=QToolButton::InstantPopup; axis_letter=A |
| page_11 | QWidget | dro_button_stack_4 | sizePolicy=0 0; maximumSize=82 64 |
| action_home_6 | ActionButton | page_11 | enabled=true; sizePolicy=0 0; minimumSize=58 38; maximumSize=82 64; focusPolicy=Qt::StrongFocus; text=GO TO ZERO; indicator_option=false; indicator_HAL_pin_option=false; on_color=0 255 0; off_color=255 0 0; indicator_size=0.200000000000000; mdi_action=false; home_action=false; mdi_command_action=true; template_label_option=false; joint_number=3; axis_letter=A; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=G90 G0 A0; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| label_gcodes | StatusLabel | frame_dro | enabled=true; sizePolicy=0 0; minimumSize=30 20; maximumSize=16777215 20; styleSheet=font: 8pt "Lato Heavy";; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; text=G0 G0 G0 G0 G0 G0 G0 G0 G0 G0 G0 G0 G0; alignment=Qt::AlignLeading&#124;Qt::AlignLeft&#124;Qt::AlignVCenter; wordWrap=false; indent=3; gcodes_status=true |
| label_mcodes | StatusLabel | frame_dro | sizePolicy=0 0; minimumSize=30 20; maximumSize=16777215 20; styleSheet=font: 8pt "Lato Heavy";; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; text=M0 M0 M0 M0 M0 M0 M0 M0 M0; alignment=Qt::AlignLeading&#124;Qt::AlignLeft&#124;Qt::AlignVCenter; wordWrap=false; indent=3; mcodes_status=true |
| frame_override | QFrame | widget_dro_ovr | sizePolicy=7 0; minimumSize=250 0; maximumSize=472 16777212; frameShape=QFrame::Box; frameShadow=QFrame::Raised |
| widget_max_ovr | QWidget | frame_override | sizePolicy=0 0 |
| widget_max_ovr | QWidget | widget_max_ovr |  |
| label_51 | QLabel | widget_max_ovr | text=MAX VELOCITY OVERRIDE; alignment=Qt::AlignCenter |
| btn_maxv_ovr_50 | QPushButton | widget_max_ovr | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; toolTip=Set max velocity override to 50%; text=50 |
| slider_maxv_ovr | StatusSlider | widget_max_ovr | sizePolicy=0 0; minimumSize=60 30; toolTip=Adjust max velocity override; maximum=3600; singleStep=10; pageStep=100; value=3600; orientation=Qt::Horizontal; pin_name=slider-override-maxv; rapid_rate=false; max_velocity_rate=true |
| btn_maxv_ovr_100 | QPushButton | widget_max_ovr | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; toolTip=Set max velocity override to 100%; text=100 |
| widget_max_info | QWidget | widget_max_ovr | sizePolicy=0 0; minimumSize=60 0; maximumSize=70 16777215 |
| status_maxvel_ovr | StatusLabel | widget_max_info | sizePolicy=0 0; minimumSize=62 26; maximumSize=62 26; toolTip=Actual max velocity rate; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; text=200; alignment=Qt::AlignCenter; textTemplate=%d; alt_textTemplate=%d; feed_override_status=false; max_velocity_override_status=true; current_feedrate_status=false; actual_spindle_speed_status=false |
| lbl_maxv_percent | StatusLabel | widget_max_info | sizePolicy=0 0; minimumSize=62 26; maximumSize=62 26; toolTip=Max velocity override; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; alignment=Qt::AlignCenter; textTemplate=%d %%; feed_override_status=false; rapid_override_status=false; jograte_status=false |
| widget_rapid_ovr | QWidget | frame_override | sizePolicy=0 0 |
| widget_rapid_ovr | QWidget | widget_rapid_ovr | minimumSize=0 0 |
| label_21 | QLabel | widget_rapid_ovr | text=RAPID OVERRIDE; alignment=Qt::AlignCenter |
| action_rapid_ovr_50 | ActionButton | widget_rapid_ovr | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; toolTip=Set rapid override to 50%; text=50; rapid_over_action=true; float_num=50.000000000000000 |
| slider_rapid_ovr | StatusSlider | widget_rapid_ovr | sizePolicy=0 0; minimumSize=60 30; toolTip=Adjust rapid rate override; maximum=100; singleStep=1; value=100; orientation=Qt::Horizontal; pin_name=slider-override-rapid; rapid_rate=true; feed_rate=false; jograte_rate=false |
| action_rapid_ovr_100 | ActionButton | widget_rapid_ovr | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; toolTip=Set rapid override to 100%; text=100; rapid_over_action=true |
| widget_rapid_info | QWidget | widget_rapid_ovr | sizePolicy=0 0; minimumSize=60 0; maximumSize=70 16777215 |
| lbl_max_rapid | StatusLabel | widget_rapid_info | sizePolicy=0 0; minimumSize=62 26; maximumSize=62 26; toolTip=Actual rapid rate; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; text=200; alignment=Qt::AlignCenter; textTemplate=%d; alt_textTemplate=%d; rapid_override_status=false; current_feedrate_status=false; actual_spindle_speed_status=false |
| status_rapid_ovr | StatusLabel | widget_rapid_info | sizePolicy=0 0; minimumSize=62 26; maximumSize=62 26; toolTip=Rapid rate override; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; alignment=Qt::AlignCenter; textTemplate=%d %%; feed_override_status=false; rapid_override_status=true; jograte_status=false |
| widget_feed_ovr | QWidget | frame_override | sizePolicy=0 0; minimumSize=0 0 |
| widget_feed_ovr | QWidget | widget_feed_ovr |  |
| label_17 | QLabel | widget_feed_ovr | text=FEEDRATE OVERRIDE; alignment=Qt::AlignCenter |
| action_feed_ovr_50 | ActionButton | widget_feed_ovr | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; toolTip=Set feedrate override to 50%; text=50; feed_over_action=true; float_num=50.000000000000000 |
| slider_feed_ovr | StatusSlider | widget_feed_ovr | sizePolicy=0 0; minimumSize=60 30; toolTip=Adjust feed rate override; maximum=120; singleStep=1; value=100; orientation=Qt::Horizontal; pin_name=slider-override-feed; feed_rate=true; jograte_rate=false |
| action_feed_ovr_100 | ActionButton | widget_feed_ovr | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; toolTip=Set feedrate override to 100%; text=100; feed_over_action=true; rapid_over_action=false; spindle_over_action=false; float_num=100.000000000000000 |
| widget_feed_info | QWidget | widget_feed_ovr | sizePolicy=0 0; minimumSize=60 0; maximumSize=70 16777215 |
| status_act_feedrate | StatusLabel | widget_feed_info | sizePolicy=0 0; minimumSize=62 26; maximumSize=62 26; toolTip=Actual feedrate; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; text=200.0; alignment=Qt::AlignCenter; textTemplate=%.1f; alt_textTemplate=%d; current_feedrate_status=true; actual_spindle_speed_status=false |
| status_feed_ovr | StatusLabel | widget_feed_info | sizePolicy=0 0; minimumSize=62 26; maximumSize=62 26; toolTip=Feedrate override; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; alignment=Qt::AlignCenter; textTemplate=%d %%; feed_override_status=true; rapid_override_status=false; spindle_override_status=false; jograte_status=false |
| widget_spindle_ovr | QWidget | frame_override | sizePolicy=0 0; minimumSize=0 0 |
| widget_spindle_ovr | QWidget | widget_spindle_ovr |  |
| label | QLabel | widget_spindle_ovr | maximumSize=16777215 16777215; text=SPINDLE OVERRIDE; alignment=Qt::AlignCenter |
| action_spindle_ovr_50 | ActionButton | widget_spindle_ovr | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; toolTip=Set spindle override to 50%; text=50; spindle_over_action=true; joint_number=0; float_num=50.000000000000000 |
| slider_spindle_ovr | StatusSlider | widget_spindle_ovr | sizePolicy=0 0; minimumSize=60 30; toolTip=Adjust spindle override; minimum=50; maximum=120; singleStep=1; value=100; orientation=Qt::Horizontal; pin_name=slider-override-spindle; rapid_rate=false; feed_rate=false; spindle_rate=true; jograte_rate=false |
| action_spindle_ovr_100 | ActionButton | widget_spindle_ovr | sizePolicy=0 0; minimumSize=40 30; maximumSize=40 30; toolTip=Set spindle override to 100%; text=100; rapid_over_action=false; spindle_over_action=true; joint_number=0 |
| widget_spindle_info | QWidget | widget_spindle_ovr | sizePolicy=0 0; minimumSize=60 0; maximumSize=70 16777215 |
| lbl_spindle_set | StatusLabel | widget_spindle_info | sizePolicy=0 0; minimumSize=62 26; maximumSize=62 26; toolTip=Requested spindle RPM; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; text=200; alignment=Qt::AlignCenter; textTemplate=%d; alt_textTemplate=%d; requested_spindle_speed_status=true; actual_spindle_speed_status=false; in_range=true |
| status_spindle_ovr | StatusLabel | widget_spindle_info | sizePolicy=0 0; minimumSize=62 26; maximumSize=62 26; toolTip=Spindle speed override; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; lineWidth=1; alignment=Qt::AlignCenter; textTemplate=%d %%; feed_override_status=false; rapid_override_status=false; spindle_override_status=true; jograte_status=false |
| page_keyboard | QWidget | stackedWidget_dro |  |
| virtualkeyboard | VirtualKeyboard | page_keyboard | sizePolicy=0 0 |
| frame_status | QFrame | screen_options | sizePolicy=0 0; minimumSize=268 290; maximumSize=300 354; frameShape=QFrame::Box; frameShadow=QFrame::Raised |
| widget_mode_buttons | QWidget | frame_status | sizePolicy=0 0; minimumSize=0 0; maximumSize=16777215 16777215 |
| manual_mode_button | ActionButton | widget_mode_buttons | sizePolicy=0 0; minimumSize=0 56; maximumSize=16777215 56; toolTip=Set to Manual mode; text=MAN; checkable=true; checked=true; autoExclusive=true; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=6; top_edge_offset=6; is_manual_status=true; manual_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm; buttonGroup=mode_buttonGroup |
| mdi_mode_button | ActionButton | widget_mode_buttons | sizePolicy=0 0; minimumSize=0 56; maximumSize=16777215 56; toolTip=Set to MDI mode; text=MDI; checkable=true; autoExclusive=true; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=6; top_edge_offset=6; is_optional_stop_status=false; is_mdi_status=true; mdi_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm; buttonGroup=mode_buttonGroup |
| auto_mode_button | ActionButton | widget_mode_buttons | sizePolicy=0 0; minimumSize=0 56; maximumSize=16777215 56; toolTip=Set to Auto mode; text=AUTO; checkable=true; autoExclusive=true; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; on_color=0 255 0; shape_option=1; indicator_size=0.200000000000000; right_edge_offset=6; top_edge_offset=6; is_auto_status=true; auto_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=100.000000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm; buttonGroup=mode_buttonGroup |
| widget_spindle_control | QWidget | frame_status | minimumSize=238 0; maximumSize=312 122 |
| label_18 | QLabel | widget_spindle_control | minimumSize=0 24; maximumSize=16777215 24; text=SPINDLE RPM; alignment=Qt::AlignCenter |
| action_spindle_rev | ActionButton | widget_spindle_control | sizePolicy=0 0; minimumSize=22 42; maximumSize=72 46; toolTip=Spindle reverse; statusTip=; text=REV; icon=../../../../../../marko/.designer/backup/images/spindle_rev.png ../../../../../../marko/.designer/backup/images/spindle_rev.png ../../../../../../marko/.designer/backup/images/spindle_rev.png; iconSize=20 20; checkable=true; autoExclusive=true; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=false; python_command_option=false; on_color=0 255 0; shape_option=1; off_color=0 0 0; indicator_size=0.300000000000000; circle_diameter=10; right_edge_offset=6; top_edge_offset=6; corner_radius=5.000000000000000; height_fraction=0.300000000000000; width_fraction=0.900000000000000; true_state_string=True; false_state_string=False; true_python_cmd_string=print"true command"; false_python_cmd_string=print"false command"; invert_the_status=false; is_paused_status=false; is_estopped_status=false; is_on_status=false; is_idle_status=false; is_homed_status=false; is_flood_status=false; is_mist_status=false; is_block_delete_status=false; is_optional_stop_status=false; is_joint_homed_status=false; is_limits_overridden_status=false; is_manual_status=false; is_mdi_status=false; is_auto_status=false; is_spindle_stopped_status=false; is_spindle_fwd_status=false; is_spindle_rev_status=true; joint_number_status=0; spindle_rev_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=0.300000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| action_spindle_fwd | ActionButton | widget_spindle_control | sizePolicy=0 0; minimumSize=22 42; maximumSize=72 46; toolTip=Spindle forward; statusTip=; text=FWD; icon=../../../../../../marko/.designer/backup/images/spindle_fwd.png ../../../../../../marko/.designer/backup/images/spindle_fwd.png ../../../../../../marko/.designer/backup/images/spindle_fwd.png; iconSize=20 20; checkable=true; autoExclusive=true; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=false; python_command_option=false; on_color=0 255 0; shape_option=1; off_color=0 0 0; indicator_size=0.300000000000000; circle_diameter=10; right_edge_offset=6; top_edge_offset=6; corner_radius=5.000000000000000; height_fraction=0.300000000000000; width_fraction=0.900000000000000; true_state_string=True; false_state_string=False; true_python_cmd_string=print"true command"; false_python_cmd_string=print"false command"; invert_the_status=false; is_paused_status=false; is_estopped_status=false; is_on_status=false; is_idle_status=false; is_homed_status=false; is_flood_status=false; is_mist_status=false; is_block_delete_status=false; is_optional_stop_status=false; is_joint_homed_status=false; is_limits_overridden_status=false; is_manual_status=false; is_mdi_status=false; is_auto_status=false; is_spindle_stopped_status=false; is_spindle_fwd_status=true; is_spindle_rev_status=false; joint_number_status=0; spindle_fwd_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=0.300000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| action_spindle_stop | ActionButton | widget_spindle_control | sizePolicy=0 0; minimumSize=22 42; maximumSize=72 46; toolTip=Spindle stop; statusTip=; text=Stop; icon=../../../../../../marko/.designer/backup/images/spindle_stop.png; iconSize=20 20; checkable=true; autoExclusive=true; indicator_option=true; indicator_HAL_pin_option=false; indicator_status_option=true; checked_state_text_option=false; python_command_option=false; on_color=255 0 0; shape_option=1; off_color=0 0 0; indicator_size=0.300000000000000; circle_diameter=10; right_edge_offset=6; top_edge_offset=6; corner_radius=5.000000000000000; height_fraction=0.300000000000000; width_fraction=0.900000000000000; true_state_string=True; false_state_string=False; true_python_cmd_string=print"true command"; false_python_cmd_string=print"false command"; invert_the_status=false; is_paused_status=false; is_estopped_status=false; is_on_status=false; is_idle_status=false; is_homed_status=false; is_flood_status=false; is_mist_status=false; is_block_delete_status=false; is_optional_stop_status=false; is_joint_homed_status=false; is_limits_overridden_status=false; is_manual_status=false; is_mdi_status=false; is_auto_status=false; is_spindle_stopped_status=true; is_spindle_fwd_status=false; is_spindle_rev_status=false; joint_number_status=0; spindle_stop_action=true; template_label_option=false; joint_number=0; incr_imperial_number=0.010000000000000; incr_mm_number=0.025000000000000; incr_angular_number=-1.000000000000000; toggle_float_option=false; float_num=0.300000000000000; float_alt_num=50.000000000000000; view_type_string=P; command_text_string=; ini_mdi_number=0; textTemplate=%1.3f in; alt_textTemplate=%1.2f mm |
| label_25 | QLabel | widget_spindle_control | text=AT SPEED; alignment=Qt::AlignCenter |
| led_at_speed | StateLED | widget_spindle_control | sizePolicy=0 0; minimumSize=24 24; maximumSize=24 24; toolTip=Spindle at speed; halpin_option=true; diameter=15; color=0 255 0; is_spindle_at_speed_status=true; halpin_name=spindle-is-at-speed |
| status_rpm | StatusLabel | widget_spindle_control | sizePolicy=0 0; minimumSize=31 40; maximumSize=16777215 40; toolTip=Current spindle RPM; frameShape=QFrame::WinPanel; frameShadow=QFrame::Sunken; alignment=Qt::AlignCenter; textTemplate=%d; actual_spindle_speed_status=true |
| widget_spindle_data | QWidget | frame_status |  |
| label_37 | QLabel | widget_spindle_data | sizePolicy=0 0; minimumSize=52 0; maximumSize=60 24; text=POWER; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; indent=1 |
| lbl_spindle_power | QLineEdit | widget_spindle_data | sizePolicy=0 0; minimumSize=34 24; maximumSize=54 24; toolTip=Spindle power; text=000; maxLength=8; cursorPosition=3; alignment=Qt::AlignCenter; readOnly=true |
| label_27 | QLabel | widget_spindle_data | minimumSize=0 24; maximumSize=16777215 24; text=MB ERRORS; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; indent=1 |
| lbl_mb_errors | QLineEdit | widget_spindle_data | sizePolicy=0 0; minimumSize=34 24; maximumSize=54 24; toolTip=Total number of modbus errors; text=0; alignment=Qt::AlignCenter; readOnly=true |
| lbl_spindle_fault | QLineEdit | widget_spindle_data | sizePolicy=0 0; minimumSize=34 24; maximumSize=54 24; toolTip=VFD fault code; text=0x0; maxLength=10; alignment=Qt::AlignCenter; readOnly=true |
| label_5 | QLabel | widget_spindle_data | sizePolicy=0 0; minimumSize=0 24; maximumSize=16777215 24; toolTip=Motion limited due to external offsets; text=FAULT CODE; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; indent=1 |
| lbl_spindle_amps | QLineEdit | widget_spindle_data | sizePolicy=0 0; minimumSize=34 24; maximumSize=54 24; font=true; mouseTracking=false; acceptDrops=false; toolTip=Spindle current; text=000; maxLength=8; cursorPosition=3; alignment=Qt::AlignCenter; readOnly=true |
| label_40 | QLabel | widget_spindle_data | sizePolicy=0 0; minimumSize=0 24; maximumSize=60 24; text=AMPS; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter; indent=1 |
| lineEdit_statusbar | QLineEdit | screen_options | sizePolicy=1 0; minimumSize=746 21; maximumSize=941 21; focusPolicy=Qt::NoFocus; autoFillBackground=false; readOnly=true; placeholderText=STATUS; clearButtonEnabled=false |
| label_47 | QLabel | screen_options | sizePolicy=0 0; minimumSize=88 21; maximumSize=88 21; text=MOTION; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter |
| statuslabel_motion | StatusLabel | screen_options | minimumSize=84 21; maximumSize=84 21; alignment=Qt::AlignCenter; motion_type_status=true; motion_type_list=Rapid Feed Arc Tool Change Probe Rotaty Index |
| label_44 | QLabel | screen_options | sizePolicy=0 0; minimumSize=80 21; maximumSize=88 21; text=RUN TIME; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter |
| lbl_runtime | StatusLabel | screen_options | minimumSize=88 21; maximumSize=88 21; text=00:00:00; alignment=Qt::AlignCenter; textTemplate=00:00:00; feed_override_status=false |
| label_11 | QLabel | screen_options | minimumSize=45 21; maximumSize=45 21; text=TIME; alignment=Qt::AlignRight&#124;Qt::AlignTrailing&#124;Qt::AlignVCenter |
| lbl_clock | StatusLabel | screen_options | sizePolicy=0 0; minimumSize=88 21; maximumSize=88 21; frameShape=QFrame::NoFrame; frameShadow=QFrame::Sunken; lineWidth=2; text=08:26:06 PM; alignment=Qt::AlignCenter; textTemplate=%I:%M:%S %p; feed_override_status=false; time_stamp_status=true |

## Indeksy stron

| Kontener | Indeks | Strona |
| --- | --- | --- |
| stackedWidget | 0 | gcode_page |
| stackedWidget | 1 | file_page |
| stackedWidget | 2 | offset_page |
| stackedWidget | 3 | tool_page |
| stackedWidget | 4 | ngcgui_page |
| stackedWidget_mainTab | 0 | stackedWidget_mainTabPage1 |
| stackedWidget_mainTab | 1 | stackedWidget_mainTabPage2 |
| stackedWidget_mainTab | 2 | stackedWidget_mainTabPage3 |
| stackedWidget_mainTab | 3 | stackedWidget_mainTabPage4 |
| stackedWidget_mainTab | 4 | stackedWidget_mainTabPage5 |
| stackedWidget_mainTab | 5 | stackedWidget_mainTabPage6 |
| stackedWidget_mainTab | 6 | stackedWidget_mainTabPage7 |
| stackedWidget_mainTab | 7 | stackedWidget_mainTabPage8 |
| stackedWidget_mainTab | 8 | stackedWidget_mainTabPage9 |
| stackedWidget_mainTab | 9 | stackedWidget_mainTabPage10 |
| stackedWidget_mainTab | 10 | main_tab_Page_Utilities |
| stackedWidget_log | 0 | page_machine |
| stackedWidget_log | 1 | page_integrator |
| tabWidget_setup | 0 | tabHTML |
| tabWidget_setup | 1 | tabPDF |
| tabWidget_setup | 2 | tabProperties |
| tabWidget_utilities | 0 | facing |
| tabWidget_utilities | 1 | hole_circle |
| tabWidget_utilities | 2 | ngcgui |
| stackedWidget_dro | 0 | page_dro |
| stackedWidget_dro | 1 | page_keyboard |
| dro_button_stack_x | 0 | page_5 |
| dro_button_stack_x | 1 | page_6 |
| dro_button_stack_y | 0 | page_7 |
| dro_button_stack_y | 1 | page_8 |
| dro_button_stack_z | 0 | page_9 |
| dro_button_stack_z | 1 | page_10 |
| dro_button_stack_5 | 0 | page_13 |
| dro_button_stack_5 | 1 | page_14 |
| dro_button_stack_5 | 2 | page |
| dro_button_stack_4 | 0 | page_2 |
| dro_button_stack_4 | 1 | page_12 |
| dro_button_stack_4 | 2 | page_11 |

## Połączenia Designer

| Nadawca | Sygnał | Odbiorca | Slot |
| --- | --- | --- | --- |
| btn_reload_file | clicked() | MainWindow | btn_reload_file_clicked() |
| action_abort | clicked() | MainWindow | disable_spindle_pause() |
| action_step | clicked() | MainWindow | disable_spindle_pause() |
| btn_spindle_pause | clicked() | MainWindow | disable_pause_buttons() |
| action_abort | clicked() | progressBar | reset() |
| btn_start | clicked() | MainWindow | btn_start_clicked() |
| btn_home_all | clicked() | MainWindow | btn_home_all_clicked() |
| btn_maxv_ovr_50 | clicked() | MainWindow | btn_maxv_50_clicked() |
| slider_maxv_ovr | valueChanged(int) | MainWindow | slider_maxv_changed() |
| slider_rapid_ovr | valueChanged(int) | MainWindow | slider_rapid_changed() |
| btn_maxv_ovr_100 | clicked() | MainWindow | btn_maxv_100_clicked() |
| btn_jog_l_slow | clicked() | MainWindow | slow_button_clicked() |
| btn_dimensions | clicked() | MainWindow | btn_dimensions_clicked() |
| cam_zoom | valueChanged(int) | MainWindow | cam_zoom_changed() |
| chk_use_tool_sensor | stateChanged(int) | MainWindow | chk_use_sensor_changed() |
| btn_gcode_edit | clicked() | MainWindow | btn_gcode_edit_clicked() |
| cam_diameter | valueChanged(int) | MainWindow | cam_dia_changed() |
| chk_use_virtual | stateChanged(int) | MainWindow | chk_use_virtual_changed() |
| chk_alpha_mode | toggled(bool) | MainWindow | chk_alpha_mode_changed() |
| btn_save_status | clicked() | MainWindow | btn_save_status_clicked() |
| chk_override_limits | toggled(bool) | MainWindow | chk_override_limits_checked() |
| cam_rotate | valueChanged(int) | MainWindow | cam_rot_changed() |
| chk_use_camera | toggled(bool) | MainWindow | chk_use_camera_changed() |
| btn_copy_left | clicked() | MainWindow | btn_copy_file_clicked() |
| chk_run_from_line | toggled(bool) | MainWindow | chk_run_from_line_checked() |
| btn_load_file | clicked() | MainWindow | btn_load_file_clicked() |
| btn_copy_right | clicked() | MainWindow | btn_copy_file_clicked() |
| btn_clear_status | clicked() | MainWindow | btn_clear_status_clicked() |
| chk_inhibit_selection | toggled(bool) | MainWindow | chk_inhibit_selection_changed() |
| btn_jog_a_slow | clicked() | MainWindow | slow_button_clicked() |
| btn_home_z | clicked() | MainWindow | btn_home_clicked() |
| btn_home_y | clicked() | MainWindow | btn_home_clicked() |
| btn_home_x | clicked() | MainWindow | btn_home_clicked() |
| pushbutton_3 | clicked(bool) | MainWindow | btn_about_clicked() |
| btn_ref_camera | clicked() | MainWindow | btn_ref_camera_clicked() |
| gcode_viewer | percentDone(int) | MainWindow | percent_done_changed() |
| btn_ref_laser | clicked() | MainWindow | btn_ref_laser_clicked() |
| cmb_gcode_history | activated(int) | MainWindow | cmb_gcode_history_clicked() |
| btn_goto_sensor | clicked() | MainWindow | btn_goto_sensor_clicked() |
| btn_touch_sensor | clicked() | MainWindow | btn_touchoff_clicked() |
| btn_touchplate | clicked() | MainWindow | btn_touchoff_clicked() |
| btn_m61 | clicked() | MainWindow | btn_m61_clicked() |
| pushbutton_6 | clicked(bool) | MainWindow | btn_spindle_z_up_clicked() |
| pushbutton_7 | clicked(bool) | MainWindow | btn_spindle_z_down_clicked() |
| pushbutton_5 | clicked(bool) | MainWindow | btn_zoomin_clicked() |
| pushbutton_4 | clicked(bool) | MainWindow | btn_zoomout_clicked() |
| tabWidget_utilities | currentChanged(int) | MainWindow | tab_utilities_changed() |
| action_home_4 | clicked() | MainWindow | btn_home_clicked() |
| action_home_5 | clicked() | MainWindow | btn_home_clicked() |
| action_pause | clicked() | MainWindow | btn_pause_clicked() |

## Widgety niestandardowe

| Klasa | Baza | Moduł |
| --- | --- | --- |
| IndicatedPushButton | QPushButton | qtvcp.widgets.simple_widgets |
| PushButton | IndicatedPushButton | qtvcp.widgets.simple_widgets |
| AxisToolButton | QToolButton | qtvcp.widgets.axis_tool_button |
| OffsetToolButton | QToolButton | qtvcp.widgets.offset_tool_button |
| FileManager | QWidget | qtvcp.widgets.file_manager |
| MachineLog | QTextEdit | qtvcp.widgets.machine_log |
| LED | QWidget | qtvcp.widgets.led_widget |
| WebWidget | QWidget | qtvcp.widgets.web_widget |
| GCodeGraphics | QWidget | qtvcp.widgets.gcode_graphics |
| DROLabel | QLabel | qtvcp.widgets.dro_widget |
| MDILine | QLineEdit | qtvcp.widgets.mdi_line |
| GcodeEditor | QWidget | qtvcp.widgets.gcode_editor |
| OriginOffsetView | QTableView | qtvcp.widgets.origin_offsetview |
| ToolOffsetView | QTableView | qtvcp.widgets.tool_offsetview |
| StateLED | LED | qtvcp.widgets.state_led |
| StatusLabel | QLabel | qtvcp.widgets.status_label |
| StateLabel | QLabel | qtvcp.widgets.state_label |
| ActionButton | IndicatedPushButton | qtvcp.widgets.action_button |
| StatusSlider | QSlider | qtvcp.widgets.status_slider |
| ScreenOptions | QWidget | qtvcp.widgets.screen_options |
| JogIncrements | QComboBox | qtvcp.widgets.jog_increments |
| CamView | QWidget | qtvcp.widgets.camview_widget |
| SystemToolButton | QToolButton | qtvcp.widgets.system_tool_button |
| ActionToolButton | QToolButton | qtvcp.widgets.action_tool_button |
| VirtualKeyboard | QWidget | qtvcp.widgets.virtualkeyboard |

## linumert_handler.py: zależności self.w

| Linia | Nazwa / wyrażenie | Dostęp |
| --- | --- | --- |
| 41 | setWindowTitle | atrybut |
| 57 | action_estop | atrybut |
| 112 | chk_override_limits | atrybut |
| 114 | chk_override_limits | atrybut |

## linumert_handler.py: sygnały i ACTION

| Linia | Wywołanie |
| --- | --- |
| 82 | self._hb_timer.timeout.connect(beat) |

## linumert_upstream_handler.py: zależności self.w

| Linia | Nazwa / wyrażenie | Dostęp |
| --- | --- | --- |
| 125 | btn_spindle_pause | atrybut |
| 169 | stackedWidget_log | atrybut |
| 170 | stackedWidget | atrybut |
| 171 | stackedWidget_dro | atrybut |
| 172 | btn_spindle_pause | atrybut |
| 173 | btn_dimensions | atrybut |
| 174 | page_buttonGroup | atrybut |
| 175 | filemanager_usb | atrybut |
| 192 | i | indeks / dynamiczne |
| 196 | i | indeks / dynamiczne |
| 199 | lbl_increments_linear | atrybut |
| 201 | widget_jog_angular | atrybut |
| 202 | widget_increments_angular | atrybut |
| 206 | 'lineEdit_' + val | indeks / dynamiczne |
| 207 | lineEdit_eoffset_count | atrybut |
| 211 | webwidget | atrybut |
| 213 | tabWidget_setup | atrybut |
| 254 | webwidget | atrybut |
| 256 | webwidget | atrybut |
| 257 | webwidget | atrybut |
| 264 | layout_PDF | atrybut |
| 270 | 'macrobutton{}'.format(b) | indeks / dynamiczne |
| 279 | frame_macro_buttons | atrybut |
| 288 | layout_facing | atrybut |
| 293 | tabWidget_utilities | atrybut |
| 299 | layout_hole_circle | atrybut |
| 304 | layout_ngcgui | atrybut |
| 305 | ngcGuiLeftLayout | atrybut |
| 343 | PREFS_ | atrybut |
| 346 | PREFS_ | atrybut |
| 347 | PREFS_ | atrybut |
| 348 | PREFS_ | atrybut |
| 348 | lineEdit_laser_x | atrybut |
| 349 | PREFS_ | atrybut |
| 349 | lineEdit_laser_y | atrybut |
| 350 | PREFS_ | atrybut |
| 350 | lineEdit_sensor_x | atrybut |
| 351 | PREFS_ | atrybut |
| 351 | lineEdit_sensor_y | atrybut |
| 352 | PREFS_ | atrybut |
| 352 | lineEdit_camera_x | atrybut |
| 353 | PREFS_ | atrybut |
| 353 | lineEdit_camera_y | atrybut |
| 354 | PREFS_ | atrybut |
| 354 | lineEdit_work_height | atrybut |
| 355 | PREFS_ | atrybut |
| 355 | lineEdit_touch_height | atrybut |
| 356 | PREFS_ | atrybut |
| 356 | lineEdit_sensor_height | atrybut |
| 357 | PREFS_ | atrybut |
| 357 | lineEdit_search_vel | atrybut |
| 358 | PREFS_ | atrybut |
| 358 | lineEdit_probe_vel | atrybut |
| 359 | PREFS_ | atrybut |
| 359 | lineEdit_max_probe | atrybut |
| 360 | PREFS_ | atrybut |
| 360 | lineEdit_retract_distance | atrybut |
| 361 | PREFS_ | atrybut |
| 361 | lineEdit_z_safe_travel | atrybut |
| 362 | PREFS_ | atrybut |
| 362 | lineEdit_eoffset_count | atrybut |
| 363 | PREFS_ | atrybut |
| 363 | chk_eoffsets | atrybut |
| 364 | PREFS_ | atrybut |
| 364 | chk_reload_program | atrybut |
| 365 | PREFS_ | atrybut |
| 365 | chk_reload_tool | atrybut |
| 366 | PREFS_ | atrybut |
| 366 | chk_use_keyboard | atrybut |
| 367 | PREFS_ | atrybut |
| 367 | chk_run_from_line | atrybut |
| 368 | PREFS_ | atrybut |
| 368 | chk_use_virtual | atrybut |
| 369 | PREFS_ | atrybut |
| 369 | chk_use_tool_sensor | atrybut |
| 370 | PREFS_ | atrybut |
| 370 | chk_use_camera | atrybut |
| 371 | PREFS_ | atrybut |
| 371 | chk_alpha_mode | atrybut |
| 372 | PREFS_ | atrybut |
| 372 | chk_inhibit_selection | atrybut |
| 373 | PREFS_ | atrybut |
| 374 | PREFS_ | atrybut |
| 375 | PREFS_ | atrybut |
| 375 | camview | atrybut |
| 378 | PREFS_ | atrybut |
| 380 | PREFS_ | atrybut |
| 381 | PREFS_ | atrybut |
| 382 | PREFS_ | atrybut |
| 383 | PREFS_ | atrybut |
| 383 | lineEdit_laser_x | atrybut |
| 384 | PREFS_ | atrybut |
| 384 | lineEdit_laser_y | atrybut |
| 385 | PREFS_ | atrybut |
| 385 | lineEdit_sensor_x | atrybut |
| 386 | PREFS_ | atrybut |
| 386 | lineEdit_sensor_y | atrybut |
| 387 | PREFS_ | atrybut |
| 387 | lineEdit_camera_x | atrybut |
| 388 | PREFS_ | atrybut |
| 388 | lineEdit_camera_y | atrybut |
| 389 | PREFS_ | atrybut |
| 389 | lineEdit_work_height | atrybut |
| 390 | PREFS_ | atrybut |
| 390 | lineEdit_touch_height | atrybut |
| 391 | PREFS_ | atrybut |
| 391 | lineEdit_sensor_height | atrybut |
| 392 | PREFS_ | atrybut |
| 392 | lineEdit_search_vel | atrybut |
| 393 | PREFS_ | atrybut |
| 393 | lineEdit_probe_vel | atrybut |
| 394 | PREFS_ | atrybut |
| 394 | lineEdit_max_probe | atrybut |
| 395 | PREFS_ | atrybut |
| 395 | lineEdit_retract_distance | atrybut |
| 396 | PREFS_ | atrybut |
| 396 | lineEdit_z_safe_travel | atrybut |
| 397 | PREFS_ | atrybut |
| 397 | lineEdit_eoffset_count | atrybut |
| 398 | PREFS_ | atrybut |
| 398 | chk_eoffsets | atrybut |
| 399 | PREFS_ | atrybut |
| 399 | chk_reload_program | atrybut |
| 400 | PREFS_ | atrybut |
| 400 | chk_reload_tool | atrybut |
| 401 | PREFS_ | atrybut |
| 401 | chk_use_keyboard | atrybut |
| 402 | PREFS_ | atrybut |
| 402 | chk_run_from_line | atrybut |
| 403 | PREFS_ | atrybut |
| 403 | chk_use_virtual | atrybut |
| 404 | PREFS_ | atrybut |
| 404 | chk_use_tool_sensor | atrybut |
| 405 | PREFS_ | atrybut |
| 405 | chk_use_camera | atrybut |
| 406 | PREFS_ | atrybut |
| 406 | chk_alpha_mode | atrybut |
| 407 | PREFS_ | atrybut |
| 407 | chk_inhibit_selection | atrybut |
| 408 | PREFS_ | atrybut |
| 409 | PREFS_ | atrybut |
| 410 | PREFS_ | atrybut |
| 410 | camview | atrybut |
| 414 | chk_override_limits | atrybut |
| 415 | chk_override_limits | atrybut |
| 416 | lbl_maxv_percent | atrybut |
| 417 | lbl_home_x | atrybut |
| 418 | lbl_home_y | atrybut |
| 419 | cmb_gcode_history | atrybut |
| 420 | cmb_gcode_history | atrybut |
| 421 | jogincrements_linear | atrybut |
| 422 | jogincrements_angular | atrybut |
| 423 | gcode_editor | atrybut |
| 424 | filemanager | atrybut |
| 425 | filemanager_usb | atrybut |
| 426 | filemanager_usb | atrybut |
| 429 | lbl_tool_sensor_B2W | atrybut |
| 430 | lbl_tool_sensor_B2S | atrybut |
| 431 | lbl_touchheight_units | atrybut |
| 432 | lbl_max_probe_units | atrybut |
| 433 | lbl_search_vel_units | atrybut |
| 434 | lbl_probe_vel_units | atrybut |
| 435 | lbl_z_ext_offset | atrybut |
| 436 | lbl_tool_sensor_loc | atrybut |
| 437 | lbl_laser_offset | atrybut |
| 438 | lbl_camera_offset | atrybut |
| 439 | lbl_touchheight_units | atrybut |
| 440 | lbl_retract_dist_units | atrybut |
| 441 | lbl_z_safe_travel_units | atrybut |
| 447 | stackedWidget_mainTab | atrybut |
| 448 | btn_user | atrybut |
| 464 | btn_probe | atrybut |
| 466 | probe_layout | atrybut |
| 470 | chk_use_virtual | atrybut |
| 473 | stackedWidget_dro | atrybut |
| 475 | stackedWidget_dro | atrybut |
| 549 | lbl_spindle_amps | atrybut |
| 550 | lbl_spindle_power | atrybut |
| 554 | lbl_spindle_fault | atrybut |
| 557 | lbl_mb_errors | atrybut |
| 561 | lbl_mb_errors | atrybut |
| 563 | lbl_mb_errors | atrybut |
| 591 | offset_table | atrybut |
| 592 | actionbutton_rel | atrybut |
| 595 | slider_rapid_ovr | atrybut |
| 597 | lbl_jog_linear | atrybut |
| 600 | lbl_jog_linear | atrybut |
| 602 | lbl_max_rapid | atrybut |
| 610 | progressBar | atrybut |
| 612 | lbl_runtime | atrybut |
| 618 | progressBar | atrybut |
| 619 | progressBar | atrybut |
| 621 | progressBar | atrybut |
| 622 | progressBar | atrybut |
| 626 | progressBar | atrybut |
| 627 | progressBar | atrybut |
| 629 | progressBar | atrybut |
| 630 | progressBar | atrybut |
| 633 | progressBar | atrybut |
| 635 | progressBar | atrybut |
| 636 | progressBar | atrybut |
| 638 | progressBar | atrybut |
| 642 | btn_home_all | atrybut |
| 645 | chk_reload_tool | atrybut |
| 648 | chk_reload_program | atrybut |
| 650 | cmb_gcode_history | atrybut |
| 651 | cmb_gcode_history | atrybut |
| 652 | cmb_gcode_history | atrybut |
| 655 | manual_mode_button | atrybut |
| 659 | btn_home_all | atrybut |
| 663 | chk_override_limits | atrybut |
| 665 | chk_override_limits | atrybut |
| 670 | chk_override_limits | atrybut |
| 672 | chk_override_limits | atrybut |
| 676 | i | indeks / dynamiczne |
| 689 | stackedWidget_mainTab | atrybut |
| 690 | stackedWidget_dro | atrybut |
| 701 | cmb_gcode_history | atrybut |
| 702 | cmb_gcode_history | atrybut |
| 719 | stackedWidget_mainTab | atrybut |
| 738 | progressBar | atrybut |
| 753 | sender | atrybut |
| 762 | action_pause | atrybut |
| 763 | action_step | atrybut |
| 767 | chk_eoffsets | atrybut |
| 768 | lineEdit_eoffset_count | atrybut |
| 788 | sender | atrybut |
| 789 | slider | indeks / dynamiczne |
| 790 | slider | indeks / dynamiczne |
| 792 | sender | atrybut |
| 793 | slider | indeks / dynamiczne |
| 794 | slider | indeks / dynamiczne |
| 795 | slider | indeks / dynamiczne |
| 797 | sender | atrybut |
| 798 | slider | indeks / dynamiczne |
| 799 | slider | indeks / dynamiczne |
| 800 | slider | indeks / dynamiczne |
| 804 | lbl_maxv_percent | atrybut |
| 808 | lbl_max_rapid | atrybut |
| 811 | slider_maxv_ovr | atrybut |
| 814 | slider_maxv_ovr | atrybut |
| 821 | filemanager | atrybut |
| 822 | widget_file_copy | atrybut |
| 823 | gcode_editor | atrybut |
| 824 | gcode_editor | atrybut |
| 826 | filemanager | atrybut |
| 827 | widget_file_copy | atrybut |
| 828 | gcode_editor | atrybut |
| 829 | gcode_editor | atrybut |
| 832 | filemanager | atrybut |
| 837 | btn_gcode_edit | atrybut |
| 838 | btn_copy_right | atrybut |
| 838 | sender | atrybut |
| 839 | filemanager_usb | atrybut |
| 840 | filemanager | atrybut |
| 841 | btn_copy_left | atrybut |
| 841 | sender | atrybut |
| 842 | filemanager | atrybut |
| 843 | filemanager_usb | atrybut |
| 863 | lineEdit_sensor_x | atrybut |
| 864 | lineEdit_sensor_y | atrybut |
| 879 | lineEdit_laser_x | atrybut |
| 880 | lineEdit_laser_y | atrybut |
| 894 | lineEdit_camera_x | atrybut |
| 895 | lineEdit_camera_y | atrybut |
| 910 | tooloffsetview | atrybut |
| 927 | sender | atrybut |
| 929 | lineEdit_max_probe | atrybut |
| 938 | machinelog | atrybut |
| 939 | lbl_clock | atrybut |
| 946 | gcodegraphics | atrybut |
| 947 | gcodegraphics | atrybut |
| 951 | camview | atrybut |
| 954 | camview | atrybut |
| 957 | camview | atrybut |
| 962 | camview | atrybut |
| 964 | camview | atrybut |
| 966 | camview | atrybut |
| 968 | camview | atrybut |
| 980 | chk_override_limits | atrybut |
| 981 | chk_override_limits | atrybut |
| 982 | chk_override_limits | atrybut |
| 987 | btn_start | atrybut |
| 990 | gcodegraphics | atrybut |
| 993 | gcodegraphics | atrybut |
| 996 | btn_ref_camera | atrybut |
| 997 | btn_camera | atrybut |
| 1000 | btn_touch_sensor | atrybut |
| 1004 | stackedWidget_dro | atrybut |
| 1010 | stackedWidget | atrybut |
| 1012 | stackedWidget | atrybut |
| 1018 | aboutDialog_ | atrybut |
| 1021 | gcode_viewer | atrybut |
| 1023 | gcode_viewer | atrybut |
| 1026 | lineEdit_eoffset_count | atrybut |
| 1031 | lineEdit_eoffset_count | atrybut |
| 1035 | lineEdit_eoffset_count | atrybut |
| 1041 | lineEdit_eoffset_count | atrybut |
| 1063 | cmb_gcode_history | atrybut |
| 1064 | cmb_gcode_history | atrybut |
| 1065 | cmb_gcode_history | atrybut |
| 1069 | filemanager | atrybut |
| 1075 | webwidget | atrybut |
| 1078 | webwidget | atrybut |
| 1096 | webwidget | atrybut |
| 1098 | stackedWidget_mainTab | atrybut |
| 1099 | stackedWidget | atrybut |
| 1100 | tabWidget_setup | atrybut |
| 1101 | btn_setup | atrybut |
| 1102 | jogging_frame | atrybut |
| 1109 | stackedWidget_mainTab | atrybut |
| 1110 | stackedWidget | atrybut |
| 1111 | tabWidget_setup | atrybut |
| 1112 | btn_setup | atrybut |
| 1113 | jogging_frame | atrybut |
| 1145 | textedit_properties | atrybut |
| 1159 | btn_spindle_pause | atrybut |
| 1160 | btn_spindle_pause | atrybut |
| 1164 | lineEdit_touch_height | atrybut |
| 1166 | lineEdit_sensor_height | atrybut |
| 1166 | lineEdit_work_height | atrybut |
| 1171 | lineEdit_max_probe | atrybut |
| 1172 | lineEdit_search_vel | atrybut |
| 1173 | lineEdit_probe_vel | atrybut |
| 1174 | lineEdit_retract_distance | atrybut |
| 1175 | lineEdit_z_safe_travel | atrybut |
| 1219 | lineEdit_statusbar | atrybut |
| 1224 | widget | indeks / dynamiczne |
| 1228 | stackedWidget_mainTab | atrybut |
| 1231 | btn_main | atrybut |
| 1240 | btn_spindle_pause | atrybut |
| 1243 | widget | indeks / dynamiczne |
| 1246 | chk_run_from_line | atrybut |
| 1248 | btn_start | atrybut |
| 1253 | chk_use_keyboard | atrybut |
| 1269 | lbl_spindle_set | atrybut |
| 1270 | lbl_spindle_set | atrybut |
| 1271 | lbl_spindle_set | atrybut |
| 1273 | lbl_spindle_set | atrybut |
| 1274 | lbl_spindle_set | atrybut |
| 1275 | lbl_spindle_set | atrybut |
| 1300 | lbl_runtime | atrybut |
| 1311 | lbl_runtime | atrybut |
| 1317 | webwidget | atrybut |
| 1319 | webwidget | atrybut |
| 1335 | webwidget | atrybut |
| 1337 | webwidget | atrybut |
| 1344 | webwidget | atrybut |
| 1347 | webwidget | atrybut |
| 1349 | webwidget | atrybut |
| 1357 | webwidget | atrybut |
| 1359 | webwidget | atrybut |
| 1366 | webwidget | atrybut |
| 1371 | webwidget | atrybut |
| 1388 | lineEdit_statusbar | atrybut |
| 1392 | lineEdit_statusbar | atrybut |
| 1395 | lineEdit_statusbar | atrybut |
| 1398 | lineEdit_statusbar | atrybut |
| 1409 | stackedWidget_mainTab | atrybut |
| 1461 | settings | atrybut |
| 1461 | splitter_h | atrybut |
| 1462 | settings | atrybut |
| 1462 | splitter_h | atrybut |
| 1463 | settings | atrybut |
| 1469 | jogging_frame | atrybut |
| 1471 | jogging_frame | atrybut |
| 1475 | stackedWidget_dro | atrybut |
| 1479 | frame_macro_buttons | atrybut |
| 1481 | frame_macro_buttons | atrybut |
| 1486 | tabWidget_utilities | atrybut |
| 1487 | stackedWidget | atrybut |
| 1489 | stackedWidget | atrybut |
| 1493 | stackedWidget | atrybut |
| 1502 | 'dro_button_stack_%s' % (n + 1) | indeks / dynamiczne |
| 1504 | 'dro_button_stack_%s' % i.lower() | indeks / dynamiczne |
| 1507 | stackedWidget_mainTab | atrybut |
| 1510 | stackedWidget_mainTab | atrybut |
| 1512 | stackedWidget_mainTab | atrybut |
| 1515 | stackedWidget_mainTab | atrybut |
| 1521 | stackedWidget_mainTab | atrybut |
| 1522 | btn_main | atrybut |
| 1526 | stackedWidget_mainTab | atrybut |
| 1537 | frame_top_left | atrybut |
| 1538 | frm_backplot | atrybut |
| 1541 | frame_top_left | atrybut |
| 1542 | frm_backplot | atrybut |
| 1545 | frame_top_left | atrybut |
| 1546 | frm_backplot | atrybut |
| 1548 | frame_top_left | atrybut |
| 1549 | frm_backplot | atrybut |
| 1556 | settings | atrybut |
| 1556 | splitter_h | atrybut |
| 1557 | settings | atrybut |
| 1558 | settings | atrybut |
| 1561 | splitter_h | atrybut |
| 1568 | 'label_axis_{}'.format(num) | indeks / dynamiczne |
| 1572 | 'dro_axis_{}'.format(num) | indeks / dynamiczne |
| 1573 | 'action_zero_{}'.format(num) | indeks / dynamiczne |
| 1574 | 'axistoolbutton_{}'.format(num) | indeks / dynamiczne |
| 1575 | 'axistoolbutton_{}'.format(num) | indeks / dynamiczne |
| 1576 | 'action_home_{}'.format(num) | indeks / dynamiczne |
| 1577 | 'action_home_{}'.format(num) | indeks / dynamiczne |
| 1578 | 'action_home_{}'.format(num) | indeks / dynamiczne |
| 1579 | 'offsettoolbutton_{}'.format(num) | indeks / dynamiczne |
| 1580 | 'plus_jogbutton_{}'.format(num) | indeks / dynamiczne |
| 1581 | 'plus_jogbutton_{}'.format(num) | indeks / dynamiczne |
| 1586 | 'plus_jogbutton_{}'.format(num) | indeks / dynamiczne |
| 1588 | 'plus_jogbutton_{}'.format(num) | indeks / dynamiczne |
| 1589 | 'minus_jogbutton_{}'.format(num) | indeks / dynamiczne |
| 1590 | 'minus_jogbutton_{}'.format(num) | indeks / dynamiczne |
| 1594 | 'minus_jogbutton_{}'.format(num) | indeks / dynamiczne |
| 1596 | 'minus_jogbutton_{}'.format(num) | indeks / dynamiczne |
| 1673 | isFullScreen | atrybut |
| 1674 | showFullScreen | atrybut |
| 1676 | isFullScreen | atrybut |
| 1677 | showNormal | atrybut |

## linumert_upstream_handler.py: sygnały i ACTION

| Linia | Wywołanie |
| --- | --- |
| 69 | KEYBIND.add_call('Key_F11', 'on_keycall_F11') |
| 70 | KEYBIND.add_call('Key_F12', 'on_keycall_F12') |
| 71 | KEYBIND.add_call('Key_Pause', 'on_keycall_pause') |
| 72 | KEYBIND.add_call('Key_Any', 'on_keycall_pause') |
| 74 | KEYBIND.add_call('Key_Period', 'on_keycall_jograte', 1) |
| 75 | KEYBIND.add_call('Key_Comma', 'on_keycall_jograte', 0) |
| 76 | KEYBIND.add_call('Key_Greater', 'on_keycall_angular_jograte', 1) |
| 77 | KEYBIND.add_call('Key_Less', 'on_keycall_angular_jograte', 0) |
| 114 | STATUS.connect('general', self.dialog_return) |
| 115 | STATUS.connect('state-on', lambda w: self.enable_onoff(True)) |
| 116 | STATUS.connect('state-off', lambda w: self.enable_onoff(False)) |
| 117 | STATUS.connect('mode-manual', lambda w: self.enable_auto(True)) |
| 118 | STATUS.connect('mode-mdi', lambda w: self.enable_auto(True)) |
| 119 | STATUS.connect('mode-auto', lambda w: self.enable_auto(False)) |
| 120 | STATUS.connect('interp-run', lambda w: self.set_button_response_state(True)) |
| 121 | STATUS.connect('interp-idle', lambda w: self.set_button_response_state(False)) |
| 122 | STATUS.connect('gcode-line-selected', lambda w, line: self.set_start_line(line)) |
| 123 | STATUS.connect('graphics-line-selected', lambda w, line: self.set_start_line(line)) |
| 124 | STATUS.connect('hard-limits-tripped', self.hard_limit_tripped) |
| 125 | STATUS.connect('program-pause-changed', lambda w, state: self.w.btn_spindle_pause.setEnabled(state)) |
| 126 | STATUS.connect('actual-spindle-speed-changed', lambda w, speed: self.update_rpm(speed)) |
| 127 | STATUS.connect('user-system-changed', lambda w, data: self.user_system_changed(data)) |
| 128 | STATUS.connect('metric-mode-changed', lambda w, mode: self.metric_mode_changed(mode)) |
| 129 | STATUS.connect('file-loaded', self.file_loaded) |
| 130 | STATUS.connect('all-homed', self.all_homed) |
| 131 | STATUS.connect('not-all-homed', self.not_all_homed) |
| 132 | STATUS.connect('periodic', lambda w: self.periodic_update()) |
| 133 | STATUS.connect('command-stopped', lambda w: self.stop_timer()) |
| 134 | STATUS.connect('progress', lambda w, p, t: self.updateProgress(p, t)) |
| 135 | STATUS.connect('override-limits-changed', lambda w, state, data: self._check_override_limits(state, data)) |
| 136 | STATUS.connect('graphics-gcode-properties', lambda w, d: self.update_gcode_properties(d)) |
| 174 | self.w.page_buttonGroup.buttonClicked.connect(self.main_tab_changed) |
| 220 | self.zoomBtn.clicked.connect(self.zoomWeb) |
| 228 | self.homeBtn.clicked.connect(self.homeWeb) |
| 236 | self.backBtn.clicked.connect(self.back) |
| 244 | self.forBtn.clicked.connect(self.forward) |
| 250 | self.writeBtn.clicked.connect(self.writer) |
| 257 | self.w.webwidget.page().urlChanged.connect(self.onLoadFinished) |
| 293 | ACTION.ADD_WIDGET_TO_TAB(self.w.tabWidget_utilities, self.hole_enlarge, 'Hole Enlarge') |
| 313 | pin.value_changed.connect(self.spindle_pwr_changed) |
| 316 | pin.value_changed.connect(self.spindle_pwr_changed) |
| 319 | pin.value_changed.connect(self.spindle_fault_changed) |
| 321 | pin.value_changed.connect(self.spindle_fault_changed) |
| 324 | pin.value_changed.connect(self.mb_errors_changed) |
| 326 | pin.value_changed.connect(self.mb_errors_changed) |
| 329 | pin.value_changed.connect(self.mb_connection_changed) |
| 582 | ACTION.SET_MACHINE_UNHOMED(-1) |
| 647 | ACTION.CALL_MDI(command) |
| 653 | ACTION.OPEN_PROGRAM(self.last_loaded_program) |
| 654 | ACTION.SET_MANUAL_MODE() |
| 706 | ACTION.OPEN_PROGRAM(filename) |
| 726 | ACTION.RUN(self.start_line) |
| 731 | ACTION.CALL_DIALOG(mess) |
| 740 | ACTION.OPEN_PROGRAM(self.last_loaded_program) |
| 745 | ACTION.SET_MACHINE_HOMING(-1) |
| 750 | ACTION.CALL_DIALOG(mess) |
| 756 | ACTION.SET_MACHINE_UNHOMED(joint) |
| 758 | ACTION.SET_MACHINE_HOMING(joint) |
| 784 | ACTION.CALL_DIALOG(mess) |
| 857 | ACTION.CALL_DIALOG(mess) |
| 873 | ACTION.CALL_MDI('G90') |
| 874 | ACTION.CALL_MDI_WAIT('G53 G0 Z0') |
| 876 | ACTION.CALL_MDI_WAIT(command, 10) |
| 891 | ACTION.CALL_MDI(command) |
| 906 | ACTION.CALL_MDI(command) |
| 915 | ACTION.CALL_MDI('M61 Q{} G43'.format(checked[0])) |
| 931 | ACTION.CALL_DIALOG(mess) |
| 975 | ACTION.TOGGLE_LIMITS_OVERRIDE() |
| 977 | ACTION.TOGGLE_LIMITS_OVERRIDE() |
| 1017 | ACTION.GET_ABOUT_INFO() |
| 1066 | ACTION.OPEN_PROGRAM(fname) |
| 1179 | ACTION.TOUCHPLATE_TOUCHOFF(search_vel, probe_vel, max_probe, z_offset, retract, safe_z, self.touchoff_return) |
| 1189 | ACTION.SET_MANUAL_MODE() |
| 1202 | ACTION.JOG(joint, direction, rate, distance) |
| 1210 | ACTION.JOG(joint, 0, 0, 0) |
| 1383 | self.timer.timeout.connect(self.clear_status_bar) |
| 1604 | ACTION.SET_ESTOP_STATE(True) |
| 1608 | ACTION.SET_MACHINE_STATE(False) |
| 1612 | ACTION.ABORT() |
| 1616 | ACTION.SET_MACHINE_HOMING(-1) |
| 1620 | ACTION.PAUSE() |
| 1625 | ACTION.SET_JOG_RATE_FASTER() |
| 1627 | ACTION.SET_JOG_RATE_SLOWER() |
| 1632 | ACTION.SET_JOG_RATE_ANGULAR_FASTER() |
| 1634 | ACTION.SET_JOG_RATE_ANGULAR_SLOWER() |

