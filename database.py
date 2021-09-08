def fetch_to_dict(db, sql, params={}, fecth='all', bind=None):
    '''
    dict的方式返回数据
    :param sql: select * from xxx where name=:name
    :param params:{'name':'zhangsan'}
    :param fecth:默认返回全部数据，返回格式为[{},{}],如果fecth='one',返回单条数据，格式为dict
    :param bind:连接的数据，默认取配置的SQLALCHEMY_DATABASE_URL，
    :return:
    '''
    resultProxy = db.session.execute(sql, params)
    if fecth == 'one':
        result_tuple = resultProxy.fetchone()
        if result_tuple:
            result = dict(zip(resultProxy.keys(), list(result_tuple)))
        else:
            return None
    else:
        result_tuple_list = resultProxy.fetchall()
        if result_tuple_list:
            result = []
            keys = resultProxy.keys()
            for row in result_tuple_list:
                result_row = dict(zip(keys, row))
                result.append(result_row)
        else:
            return None
    return result