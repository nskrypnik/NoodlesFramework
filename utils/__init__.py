from maputils import *
import datetime
import decimal


dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else obj


def datahandler(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    return obj
