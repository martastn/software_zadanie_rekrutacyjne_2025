import sys
from time import sleep
from controller import Controller

def wait_until_filled(name, value):
    while (
        not controller.rocket_status["sensors"]
        or not controller.rocket_status["sensors"].get(name)
        or controller.rocket_status["sensors"].get(name) < value
    ):
        sleep(0.5)
    return 1


if __name__ == "__main__":
    
    controller = Controller("127.0.0.1", 3000, print_logs=False)

    # tankowanie utleniacza
    controller.set_servo(1, 0)
    wait_until_filled("oxidizer_level", 100)
    controller.set_servo(1, 100)

    # tankowanie paliwa
    controller.set_servo(0, 0)
    wait_until_filled("fuel_level", 100)
    controller.set_servo(0, 100)

    # podgrzewanie utleniacza
    controller.toggle_relay(0, 1)
    wait_until_filled("oxidizer_pressure", 55)

    # sekwencja zapłonu
    controller.set_servo(2, 0)
    controller.set_servo(3, 0)
    controller.toggle_relay(1, 1)

    # lot
    h1 = controller.rocket_status["sensors"].get('altitude')
    sleep(0.5)
    h2 = controller.rocket_status["sensors"].get('altitude')
    while h2 >= h1:
        sleep(0.5)
        h1 = h2
        h2 = controller.rocket_status["sensors"].get('altitude')
        
    v = (h2-h1)/0.5
    while v > 30:
        sleep(0.5)
        h1 = h2
        h2 = controller.rocket_status["sensors"].get('altitude')

    # lądowanie
    controller.toggle_relay(1, 0)
    controller.toggle_relay(2, 1)

    while controller.rocket_status["sensors"].get('altitude') > 1:
        sleep(1)

    sys.exit()
    