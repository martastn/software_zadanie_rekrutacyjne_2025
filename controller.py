import sys
import threading
from time import sleep, time
import yaml
from communication_library.exceptions import TransportTimeoutError, UnknownCommand, UnregisteredCallbackError, WrongOperationOrderCLI
from communication_library.frame import ids, Frame
from communication_library.communication_manager import CommunicationManager, TransportType
from communication_library.tcp_transport import TcpSettings
from argparse import ArgumentParser
import traceback
from nicegui import ui

class Controller:
    def __init__(self, proxy_address, proxy_port, keep_running = True, print_logs = True, hardware_config: str = 'simulator_config.yaml'):
        
        with open(hardware_config, 'r') as config_file:
            self.config = yaml.safe_load(config_file)
        
        self.manager = CommunicationManager()
        self.manager.change_transport_type(TransportType.TCP)
        self.manager.connect(TcpSettings(address=proxy_address, port=proxy_port))

        self.rocket_status = {
            "sensors": {},
            "servos": {},
            "relays": {}
        }

        self._initialize_from_controller()
        self.print_logs = print_logs

        self.sensor_id_map = {cfg["device_id"]: name
                              for name, cfg in self.config["devices"]["sensor"].items()}
        self.servo_id_map = {cfg["device_id"]: name
                             for name, cfg in self.config["devices"]["servo"].items()}
        self.relay_id_map = {cfg["device_id"]: name
                             for name, cfg in self.config["devices"]["relay"].items()}
        
        self.servo_name_to_id = {name: cfg["device_id"]
                         for name, cfg in self.config["devices"]["servo"].items()}
        
        self.relay_name_to_id = {name: cfg["device_id"]
                         for name, cfg in self.config["devices"]["relay"].items()}

        self.should_keep_running = keep_running
        self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._receive_thread.start()

    def _initialize_from_controller(self):
        for name in self.config["devices"]["sensor"].keys():
            self.rocket_status['sensors'][name] = 0
            
        for name in self.config["devices"]["servo"].keys():
            self.rocket_status['servos'][name] = 100
            
        for name in self.config["devices"]["relay"].keys():
            self.rocket_status['relays'][name] = False

    def set_servo(self, device_id: int, position: int):

        # v, e = self.validate_change('servo', self.servo_id_map[device_id], position)
        # if not v:
        #     print(e)
        #     return

        frame = Frame(
            destination=ids.BoardID.ROCKET,
            priority=ids.PriorityID.LOW,
            action=ids.ActionID.SERVICE,
            source=ids.BoardID.SOFTWARE,
            device_type=ids.DeviceID.SERVO,
            device_id=device_id,
            data_type=ids.DataTypeID.INT16,
            operation=ids.OperationID.SERVO.value.POSITION,
            payload=(position,)
        )
        self.manager.push(frame)
        self.manager.send()

    def toggle_relay(self, device_id: int, state: bool):
        operation_id = (ids.OperationID.RELAY.value.OPEN if state 
                        else ids.OperationID.RELAY.value.CLOSE)
        
        # v, e = self.validate_change('relay', self.relay_id_map[device_id], state)
        # if not v:
        #     print(e)
        #     return
        
        frame = Frame(
            destination=ids.BoardID.ROCKET,
            priority=ids.PriorityID.LOW,
            action=ids.ActionID.SERVICE,
            source=ids.BoardID.SOFTWARE,
            device_type=ids.DeviceID.RELAY,
            device_id=device_id,
            data_type=ids.DataTypeID.NO_DATA,
            operation=operation_id,
            payload=()
        )
        
        self.manager.push(frame)
        self.manager.send()
        self.rocket_status["relays"][self.relay_id_map[device_id]] = state

    def _receive_loop(self):
        
        while self.should_keep_running:
            try:
                frame = self.manager.receive()
                self._process_frame(frame)
                
            except TransportTimeoutError:
                sleep(0.5)
                continue
                
            except UnregisteredCallbackError as e:
                frame = e.frame
                self._process_frame(frame)
                
            except KeyboardInterrupt:
                sys.exit()

    def _process_frame(self, frame: Frame):
        if frame.action == ids.ActionID.FEED:
            if frame.device_type == ids.DeviceID.SENSOR:
                sensor_name = self.sensor_id_map.get(frame.device_id)
                if sensor_name: self.rocket_status["sensors"][sensor_name] = frame.data

            elif frame.device_type == ids.DeviceID.SERVO:
                servo_name = self.servo_id_map.get(frame.device_id)
                if servo_name: self.rocket_status["servos"][servo_name] = frame.data

        if frame.action == ids.ActionID.FEED:
            if self.print_logs: self.print_rocket_status()

    def print_rocket_status(self):
        try:
            print("=== ROCKET STATUS  ===")

            print("SENSORS:")
            for name, value in sorted(self.rocket_status["sensors"].items()):
                print(f"  - {name:<20} : {value:.3f}")

            print("\nSERVOS:")
            for name, value in sorted(self.rocket_status["servos"].items()):
                print(f"  - {name:<20} : {value}")

            print("\nRELAYS:")
            for name, value in sorted(self.rocket_status["relays"].items()):
                value = "CLOSED" if value == False else "OPEN"
                print(f"  - {name:<20} : {value}")

            print("=" * 30)
        except Exception as e:
            print(f"Error printing rocket status: {e}")

    def close(self):
        self.should_keep_running = False
        if hasattr(self, '_receive_thread') and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=3.0)
        self.manager.disconnect()

    def validate_change(self, type, name, value):
        if type == 'servo' and name == 'fuel_intake' and value == 0:
             if self.rocket_status['servos']['oxidizer_intake'] == 0 or self.rocket_status['sensors']['oxidizer_level'] != 100:
                 return 0, 'Fill and close oxidizer_intake before opening fuel_intake'
            
        if type == 'relay' and name == 'igniter' and value == 1:
            if self.rocket_status['servos']['oxidizer_main'] != 0 or self.rocket_status['sensors']['fuel_main'] != 0:
                 return 0, 'Open fuel_main and oxidizer_main before turning on igniter'
            if self.rocket_status['sensors']['oxidizer_pressure'] < 40:
                 return 0, 'Oxidizer pressure too low'
            if self.rocket_status['sensors']['oxidizer_pressure'] > 65:
                 return 0, 'Oxidizer pressure too high'
            if self.rocket_status['servos']['oxidizer_intake'] != 100 or self.rocket_status['servos']['fuel_intake'] != 100:
                return 0, 'Close intakes'
             
        if type == 'relay' and name == 'parachute' and value == 1:
            if self.rocket_status['relays']['igniter'] == 1:
                return 0, 'Turn off igniter'
            
        return 1, 'correct'


def main_cli(controller):
    
    try:
        if cl_args.operation is not None and cl_args.device_id is not None and cl_args.new_value is not None:

            if cl_args.operation == 'set_servo':
                v, e = controller.validate_change('servo', controller.servo_id_map[cl_args.device_id], int(cl_args.new_value))
                if not v: 
                    controller.close()
                    raise WrongOperationOrderCLI(e)
                else: controller.set_servo(int(cl_args.device_id), int(cl_args.new_value))

            elif cl_args.operation == 'toggle_relay':
                v, e = controller.validate_change('relay', controller.relay_id_map[cl_args.device_id], int(cl_args.new_value))
                if not v: 
                    controller.close()
                    raise WrongOperationOrderCLI(e)
                else: controller.toggle_relay(int(cl_args.device_id), cl_args.new_value.lower() == 'true')

            else:
                controller.close()
                raise UnknownCommand('Unknown operation name')
    
        while controller.should_keep_running: 
            sleep(0.5)
        controller.close()
            
    except KeyboardInterrupt:
        controller.close()
        sys.exit()

        

def main_gui(controller):
    try:
        toggles = {}
        toggle_labels = {}
        sliders = {}
        sliders_labels = {}

        def refresh_slider(name):
            controller.set_servo(controller.servo_name_to_id[name], sliders[name].value)

        def refresh_relay(e, name):
            new_value = e.value
            state = (new_value == "OPEN")
            controller.toggle_relay(controller.relay_name_to_id[name], state)

        with ui.card().classes('w-full'):
            ui.label("Device Controlling").classes('text-lg font-bold mb-4')

            for name in controller.config["devices"]["relay"].keys():
                toggle_labels[name] = ui.label(name)
                toggles[name] = ui.toggle(
                    ["OPEN", "CLOSED"],
                    value="CLOSED",
                    on_change=lambda e, n=name: refresh_relay(e, n)
                )

            for name in controller.config["devices"]["servo"].keys():
                with ui.card().classes('w-full'):
                    sliders_labels[name] = ui.label(name)
                    sliders[name] = ui.slider(
                        min=0, max=100, value=100,
                        on_change=lambda e, n=name: refresh_slider(n)
                    ).props('label-always')

        ui.run(title='Rocket Controller', host='0.0.0.0', port=8082, reload=False)

    except KeyboardInterrupt:
        controller.close()
        sys.exit()



if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--proxy-address', default="127.0.0.1")
    parser.add_argument('--proxy-port', type=int, default=3000)
    parser.add_argument('--control-type', choices=['gui', 'cli'], required=True)
    parser.add_argument('--operation', choices=['set_servo', 'toggle_relay'])
    parser.add_argument('--device-id', type=int)
    parser.add_argument('--new-value')
    parser.add_argument('--keep-running', default = 'yes', choices=['yes', 'no'])
    parser.add_argument('--print-logs', default = 'yes', choices=['yes', 'no'])
    cl_args = parser.parse_args()

    if cl_args.keep_running == 'yes':
        keep_running = True
    elif cl_args.keep_running == 'no':
        keep_running = False
    else:
        raise UnknownCommand('Invalid --keep-running value')
    
    if cl_args.print_logs == 'yes':
        print_logs = True
    elif cl_args.print_logs == 'no':
        print_logs = False
    else:
        raise UnknownCommand('Invalid --print-logs value')

    try:
        controller = Controller(cl_args.proxy_address, cl_args.proxy_port, keep_running, print_logs)

        if cl_args.control_type == 'gui': 
            main_gui(controller)
        elif cl_args.control_type == 'cli':
            main_cli(controller)
        else:
            raise UnknownCommand('Invalid --control-type value')
            
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()