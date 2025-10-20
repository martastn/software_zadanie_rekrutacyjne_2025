import random
import sys
import time
import os
import yaml

from communication_library.frame import ids, Frame
from communication_library.communication_manager import CommunicationManager, TransportType
from communication_library.exceptions import UnregisteredCallbackError

from communication_library.exceptions import TransportTimeoutError # pylint: disable=ungrouped-imports
from communication_library.tcp_transport import TcpSettings        # pylint: disable=ungrouped-imports

from argparse import ArgumentParser

import logging


class StandaloneMock:
    def __init__(self, proxy_address: str,
                 proxy_port: int,
                 hardware_config: str,
                 feed_send_interval: float,
                 no_print: bool):
        
        with open(hardware_config, 'r') as config_file:
            self.config = yaml.safe_load(config_file)
        
        self.manager = CommunicationManager()
        self.manager.change_transport_type(TransportType.TCP)
        self.manager.connect(TcpSettings(address=proxy_address, port=proxy_port))
        self.setup_loggers()
        self._logger = logging.getLogger("main")
        self.feed_send_delay = feed_send_interval
        self.no_print = no_print
        self.last_feed_update = time.perf_counter()
        self.should_run = True

        self._logger.info(
            f'Standalone mock is running connected to {proxy_address}:{proxy_port}')

    def setup_loggers(self):
        logger_main = logging.getLogger("main")
        logger_main.setLevel(logging.DEBUG)

        fmt = '[%(asctime)s] [%(levelname)s] %(message)s'
        log_formatter = logging.Formatter(fmt=fmt)

        console_handler = logging.StreamHandler(sys.stdout)

        console_handler.setFormatter(log_formatter)
        logger_main.addHandler(console_handler)

    def get_response_id_for_action(self, frame_action, nack_weight=0, snack_weight=0):
        ack_weights = [1 - nack_weight, nack_weight]
        sack_weights = [1 - snack_weight, snack_weight]
        action = random.choices([ids.ActionID.ACK, ids.ActionID.NACK], ack_weights, k=1)[0]
        if frame_action == ids.ActionID.REQUEST:
            action = ids.ActionID.RESPONSE
        if frame_action == ids.ActionID.SCHEDULE:
            action = random.choices([ids.ActionID.SACK, ids.ActionID.SNACK], sack_weights, k=1)[0]
        return action

    def handle_frame(self, _frame) -> list[Frame]:
        action = self.get_response_id_for_action(_frame.action)
        output_frames = []
        if _frame.destination == ids.BoardID.BROADCAST:
            frame_params = _frame.as_dict()
            replacements = {'destination': _frame.source, 'source': _frame.destination, 'action': action}
            output_frames.append(Frame(**{**_frame.as_dict(), **replacements}))
            for board in [ids.BoardID.STASZEK, ids.BoardID.KROMEK]:
                frame_params['source'] = ids.BoardID.SOFTWARE
                frame_params['destination'] = board
                new_frame = self.handle_frame(Frame(**frame_params))[0]
                output_frames.append(new_frame)
            return output_frames

        replacements = {'destination': _frame.source, 'source': _frame.destination, 'action': action}
        output_frames.append(Frame(**{**_frame.as_dict(), **replacements}))
        return output_frames

    def send_feed_frame(self):
        conf_dict = self.config
        servos: dict = conf_dict["devices"]["servo"]
        dynamixels: dict = conf_dict["devices"]["dynamixel"]
        sensors: dict = conf_dict["devices"]["sensor"]
        pistons: dict = conf_dict["devices"]["piston"]
        sensors.update(pistons)
        for sensor_settings in sensors.values():
            source = ids.BoardID[sensor_settings["board"].upper()]
            device_id = sensor_settings["device_id"]
            data_type = ids.DataTypeID[sensor_settings["data_type"].upper()]
            if data_type == ids.DataTypeID.INT8:
                value = random.randint(-127, 127)
            elif data_type == ids.DataTypeID.UINT8:
                value = random.randint(0, 255)
            elif data_type == ids.DataTypeID.INT16:
                value = random.randint(-32767, 32767)
            else:
                value = random.randint(0, 65535)

            if device_id == 2:
                value = random.randint(0, 1000)

            frame = Frame(destination=ids.BoardID.SOFTWARE,
                          priority=ids.PriorityID.LOW,
                          action=ids.ActionID.FEED,
                          source=source,
                          device_type=ids.DeviceID.SENSOR,
                          device_id=device_id,
                          data_type=data_type,
                          operation=ids.OperationID.SENSOR.value.READ,
                          payload=(value,))
            self.manager.push(frame)
            try:
                self.manager.send()
            except TransportTimeoutError:
                break

            if not self.no_print:
                self._logger.info(f"sent feed frame: {frame}")

        for dynamixel_settings in dynamixels.values():
            source = ids.BoardID[dynamixel_settings["board"].upper()]
            device_id = dynamixel_settings["device_id"]
            data_type = ids.DataTypeID.INT16
            value = random.randint(-2000, 4000)

            frame = Frame(destination=ids.BoardID.SOFTWARE,
                          priority=ids.PriorityID.LOW,
                          action=ids.ActionID.FEED,
                          source=source,
                          device_type=ids.DeviceID.DYNAMIXEL,
                          device_id=device_id,
                          data_type=data_type,
                          operation=ids.OperationID.DYNAMIXEL.value.POSITION,
                          payload=(value,))
            self.manager.push(frame)
            try:
                self.manager.send()
            except TransportTimeoutError:
                break

            if not self.no_print:
                self._logger.info(f"sent feed frame: {frame}")

        for servo_settings in servos.values():
            source = ids.BoardID[servo_settings["board"].upper()]
            device_id = servo_settings["device_id"]
            data_type = ids.DataTypeID.INT16
            value = random.randint(-2000, 4000)

            frame = Frame(destination=ids.BoardID.SOFTWARE,
                          priority=ids.PriorityID.LOW,
                          action=ids.ActionID.FEED,
                          source=source,
                          device_type=ids.DeviceID.SERVO,
                          device_id=device_id,
                          data_type=data_type,
                          operation=ids.OperationID.SERVO.value.POSITION,
                          payload=(value,))
            self.manager.push(frame)
            try:
                self.manager.send()
            except TransportTimeoutError:
                break

            if not self.no_print:
                self._logger.info(f"sent feed frame: {frame}")

    def receive_send_loop(self):
        while self.should_run:
            try:
                frame = self.manager.receive()
            except TransportTimeoutError:
                continue
            except UnregisteredCallbackError as e:
                frame = e.frame
            except KeyboardInterrupt:
                sys.exit()
            finally:
                if time.perf_counter() > self.last_feed_update + float(self.feed_send_delay):
                    self.send_feed_frame()
                    self.last_feed_update = time.perf_counter()

            for frame in self.handle_frame(frame):
                self.manager.push(frame)
                if not self.no_print:
                    self._logger.info(f"pushed frame: {frame}")
                try:
                    self.manager.send()
                except TransportTimeoutError:
                    continue


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--proxy-address', default="127.0.0.1")
    parser.add_argument('--proxy-port', default=3001)
    parser.add_argument('--feed-interval', default=1)
    parser.add_argument('--hardware-config', default='simulator_config.yaml')
    parser.add_argument('--no-print', default=False, action='store_true')
    cl_args = parser.parse_args()
    standalone_mock = StandaloneMock(cl_args.proxy_address,
                                     int(cl_args.proxy_port),
                                     cl_args.hardware_config,
                                     cl_args.feed_interval,
                                     cl_args.no_print)
    standalone_mock.receive_send_loop()