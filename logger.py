import logging


def init_logger(name):
    logger = logging.getLogger(name)
    FORMAT = "%(asctime)s :: %(name)s:%(lineno)s :: %(levelname)s :: %(message)s"
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(FORMAT))
    logger.setLevel(logging.DEBUG)
    sh.setLevel(logging.DEBUG)
    logger.addHandler(sh)
    logger.debug("Логирование запущено.")
    return logger
