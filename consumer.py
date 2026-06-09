from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Consumer

if __name__=="__main__":

    # Parse command-line arguments
    parser = ArgumentParser()
    parser.add_argument("config_file", type=FileType("r"))
    args = parser.parse_args()

    # Parse configuration file
    config_parser = ConfigParser()
    config_parser.read_file(args.config_file)
    config = dict(config_parser["default"])
    config.update(config_parser["consumer"])

    #Create Consumer instance
    consumer = Consumer(config)

    # Subscribe to topic
    topic = "poems"
    consumer.subscribe([topic])

    # Poll for messages
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                print("Waiting for message...")
            elif msg.error():
                print(msg.error())
            else:
                key = msg.key().decode("utf-8") if msg.key() is not None else None
                value = msg.value().decode("utf-8") if msg.value() is not None else None
                print(f"Consumed event from topic {msg.topic()}: Key = {key}, value = {value}")
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()