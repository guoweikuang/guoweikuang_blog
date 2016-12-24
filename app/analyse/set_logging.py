import logging

# logger = logging.getLogger()
# handler = logging.StreamHandler()
# fh = logging.FileHandler('print.log')
# fh.setLevel(logging.)
# formatter = logging.Formatter(
#     '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)
# logger.setLevel(logging.DEBUG)


def save_to_logging(contents):
    logging.basicConfig(
        filename='print.log',
        level=logging.DEBUG,
        format='%(levelname)s:%(asctime)s:%(message)s'
    )
    logging.info(contents)