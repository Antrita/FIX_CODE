from multiprocessing.forkserver import connect_to_new_process
from socket import create_connection

import PySimpleGUI as sg
import threading
import queue

# Assuming you have these functions in your client script
from Client import Client


def create_main_window():
    sg.theme('LightGrey1')

    layout = [
        [sg.Text('FIX Simulator Client', font=('Helvetica', 16))],
        [sg.Text('Server Status:'), sg.Text('Disconnected', key='-STATUS-', text_color='red')],
        [sg.Button('Connect'), sg.Button('Disconnect')],
        [sg.Text('Order Details:')],
        [sg.Text('Symbol:'), sg.Input(key='-SYMBOL-', size=(10, 1))],
        [sg.Text('Side:'), sg.Combo(['Buy', 'Sell'], key='-SIDE-', size=(10, 1))],
        [sg.Text('Quantity:'), sg.Input(key='-QUANTITY-', size=(10, 1))],
        [sg.Text('Price:'), sg.Input(key='-PRICE-', size=(10, 1))],
        [sg.Button('Send Order'), sg.Button('Cancel Order')],
        [sg.Text('Messages:')],
        [sg.Multiline(size=(60, 10), key='-MESSAGES-', disabled=True)],
        [sg.Button('Exit')]
    ]

    return sg.Window('FIX Simulator', layout, finalize=True)


def main():
    window = create_main_window()
    connected = False
    message_queue = queue.Queue()

    def update_messages():
        try:
            while True:
                message = message_queue.get_nowait()
                window['-MESSAGES-'].print(message)
        except queue.Empty:
            pass

    while True:
        event, values = window.read(timeout=100)

        if event == sg.WINDOW_CLOSED or event == 'Exit':
            break

        if event == 'Connect' and not connected:
            connected = Client()
            if connected:
                window['-STATUS-'].update('Connected', text_color='green')

        elif event == 'Disconnect' and connected:
            # Implement disconnect logic here
            connected = False
            window['-STATUS-'].update('Disconnected', text_color='red')

        elif event == 'Send Order' and connected:
            order = {
                'symbol': values['-SYMBOL-'],
                'side': values['-SIDE-'],
                'quantity': values['-QUANTITY-'],
                'price': values['-PRICE-']
            }
            threading.Thread(target=Client.place_order, args=('buy', 'sell', order, message_queue)).start()

        elif event == 'Cancel Order' and connected:
            # Implement cancel order logic here
            pass

        update_messages()

    window.close()


if __name__ == '__main__':
    main()


