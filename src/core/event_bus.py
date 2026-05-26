import threading

from core.logger import Logger


class EventBus:

    def __init__(self):

        self.listeners = {}

        self.lock = threading.RLock()

    def subscribe(self, event_name, callback):

        with self.lock:

            if event_name not in self.listeners:

                self.listeners[event_name] = []

            self.listeners[event_name].append(callback)

        def unsubscribe():

            self.unsubscribe(event_name, callback)

        return unsubscribe

    def unsubscribe(self, event_name, callback):

        with self.lock:

            callbacks = self.listeners.get(event_name, [])

            if callback in callbacks:

                callbacks.remove(callback)

    def emit(self, event_name, data=None):

        with self.lock:

            callbacks = list(self.listeners.get(event_name, []))

        for callback in callbacks:

            try:
                callback(data)

            except Exception as error:
                Logger.error(
                    f"Event listener failed | event={event_name} | error={error}"
                )
