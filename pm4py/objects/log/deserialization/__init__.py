try:
    # for Windows 32 compatibility
    import pyarrow
    from pm4py.objects.log.deserialization import algorithm, versions
except:
    # do not import the serialization package
    pass
