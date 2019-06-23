"""Testing for OmegaConf"""
import copy
import re
import tempfile

from pytest import raises

from omegaconf import MissingMandatoryValue
from omegaconf import OmegaConf, DictConfig, ListConfig


def test_setattr_value():
    c = OmegaConf.create('a: {b : {c: 1}}')
    c.a = 9
    assert {'a': 9} == c


def test_setattr_deep_value():
    c = OmegaConf.create('a: {b : {c: 1}}')
    c.a.b = 9
    assert {'a': {'b': 9}} == c


def test_setattr_deep_from_empty():
    c = OmegaConf.create()
    # Unfortunately we can't just do c.a.b = 9 here.
    # The reason is that if c.a is being resolved first and it does not exist, so there
    # is nothing to call .b = 9 on.
    # The alternative is to auto-create fields as they are being accessed, but this is opening
    # a whole new can of worms, and is also breaking map semantics.
    c.a = {}
    c.a.b = 9
    assert {'a': {'b': 9}} == c


def test_setattr_deep_map():
    c = OmegaConf.create('a: {b : {c: 1}}')
    c.a.b = {'z': 10}
    assert {'a': {'b': {'z': 10}}} == c


def test_dir():
    c = OmegaConf.create('a: b')
    assert ['a'] == dir(c)


def test_getattr():
    c = OmegaConf.create('a: b')
    assert 'b' == c.a


def test_getattr_dict():
    c = OmegaConf.create('a: {b: 1}')
    assert {'b': 1} == c.a


def test_str():
    c = OmegaConf.create('a: b')
    assert "{'a': 'b'}" == str(c)


def test_repr_dict():
    c = OmegaConf.create(dict(a='b'))
    assert "{'a': 'b'}" == repr(c)


def test_repr_list():
    c = OmegaConf.create([1, 2, 3])
    assert "[1, 2, 3]" == repr(c)


def test_is_empty_dict():
    c = OmegaConf.create('a: b')
    assert not c.is_empty()
    c = OmegaConf.create()
    assert c.is_empty()


def test_is_empty_list():
    c = OmegaConf.create('[1,2,3]')
    assert not c.is_empty()
    c = OmegaConf.create([])
    assert c.is_empty()


def test_list_value():
    c = OmegaConf.create('a: [1,2]')
    assert {'a': [1, 2]} == c


def test_list_of_dicts():
    v = [
        dict(key1='value1'),
        dict(key2='value2')
    ]
    c = OmegaConf.create(v)
    assert c[0].key1 == 'value1'
    assert c[1].key2 == 'value2'


def test_mandatory_value():
    c = OmegaConf.create(dict(a='???'))
    with raises(MissingMandatoryValue, match='a'):
        c.a


def test_nested_dict_mandatory_value():
    c = OmegaConf.create(dict(a=dict(b='???')))
    with raises(MissingMandatoryValue):
        c.a.b


def test_mandatory_with_default():
    c = OmegaConf.create(dict(name='???'))
    assert c.get('name', 'default value') == 'default value'


def test_subscript_get():
    c = OmegaConf.create('a: b')
    assert 'b' == c['a']


def test_subscript_set():
    c = OmegaConf.create()
    c['a'] = 'b'
    assert {'a': 'b'} == c


def test_pretty_dict():
    c = OmegaConf.create(dict(
        hello='world',
        list=[
            1,
            2
        ]
    ))
    expected = '''hello: world
list:
- 1
- 2
'''
    assert expected == c.pretty()
    assert OmegaConf.create(c.pretty()) == c


def test_pretty_list():
    c = OmegaConf.create([
        'item1',
        'item2',
        dict(key3='value3')
    ])
    expected = '''- item1
- item2
- key3: value3
'''
    assert expected == c.pretty()
    assert OmegaConf.create(c.pretty()) == c


def test_scientific_notation_float():
    c = OmegaConf.create('a: 10e-3')
    assert 10e-3 == c.a


def test_dict_get_with_default():
    s = '{hello: {a : 2}}'
    c = OmegaConf.create(s)
    assert c.get('missing', 4) == 4
    assert c.hello.get('missing', 5) == 5


def test_list_get_with_default():
    c = OmegaConf.create([None, "???", "found"])
    assert c.get(0, 'default_value') == 'default_value'
    assert c.get(1, 'default_value') == 'default_value'
    assert c.get(2, 'default_value') == 'found'


def test_map_expansion():
    c = OmegaConf.create('{a: 2, b: 10}')

    def foo(a, b):
        return a + b

    assert 12 == foo(**c)


def test_items():
    c = OmegaConf.create('{a: 2, b: 10}')
    assert {'a': 2, 'b': 10}.items() == c.items()


def test_dict_keys():
    c = OmegaConf.create('{a: 2, b: 10}')
    assert {'a': 2, 'b': 10}.keys() == c.keys()


def test_pickle_get_root():
    # Test that get_root() is reconstructed correctly for pickle loaded files.
    with tempfile.TemporaryFile() as fp:
        c1 = OmegaConf.create(dict(
            a=dict(
                a1=1,
                a2=2,
            ),
        ))

        c2 = OmegaConf.create(dict(
            b=dict(
                b1='???',
                b2=4,
                bb=dict(
                    bb1=3,
                    bb2=4,
                ),
            ),
        ))
        c3 = OmegaConf.merge(c1, c2)

        import pickle
        pickle.dump(c3, fp)
        fp.flush()
        fp.seek(0)
        loaded_c3 = pickle.load(fp)

        def test(conf):
            assert conf._get_root() == conf
            assert conf.a._get_root() == conf
            assert conf.b._get_root() == conf
            assert conf.b.bb._get_root() == conf

        assert c3 == loaded_c3
        test(c3)
        test(loaded_c3)


def test_iterate_dictionary():
    c = OmegaConf.create('''
    a : 1
    b : 2
    ''')
    m2 = {}
    for key in c:
        m2[key] = c[key]
    assert m2 == c


def test_iterate_list():
    c = OmegaConf.create([1, 2])
    items = [x for x in c]
    assert items[0] == 1
    assert items[1] == 2


def test_items():
    c = OmegaConf.create('''
    a:
      v: 1
    b:
      v: 1
    ''')
    for k, v in c.items():
        v.v = 2

    assert c.a.v == 2
    assert c.b.v == 2


def test_dict_pop():
    c = OmegaConf.create(dict(a=1, b=2))
    assert c.pop('a') == 1
    assert c.pop('not_found', 'default') == 'default'
    assert c == {'b': 2}
    with raises(KeyError):
        c.pop('not_found')


def test_list_pop():
    c = OmegaConf.create([1, 2, 3, 4])
    assert c.pop(0) == 1
    assert c.pop() == 4
    assert c == [2, 3]
    with raises(IndexError):
        c.pop(100)


def test_in_dict():
    c = OmegaConf.create(dict(
        a=1,
        b=2,
        c={}))
    assert 'a' in c
    assert 'b' in c
    assert 'c' in c
    assert 'd' not in c


def test_in_list():
    c = OmegaConf.create([10, 11, dict(a=12)])
    assert 10 in c
    assert 11 in c
    assert dict(a=12) in c
    assert 'blah' not in c


def test_get_root():
    c = OmegaConf.create(dict(
        a=123,
        b=dict(
            bb=456,
            cc=7,
        ),
    ))
    assert c._get_root() == c
    assert c.b._get_root() == c


def test_get_root_of_merged():
    c1 = OmegaConf.create(dict(
        a=dict(
            a1=1,
            a2=2,
        ),
    ))

    c2 = OmegaConf.create(dict(
        b=dict(
            b1='???',
            b2=4,
            bb=dict(
                bb1=3,
                bb2=4,
            ),
        ),
    ))
    c3 = OmegaConf.merge(c1, c2)

    assert c3._get_root() == c3
    assert c3.a._get_root() == c3
    assert c3.b._get_root() == c3
    assert c3.b.bb._get_root() == c3


def test_deepcopy():
    c1 = OmegaConf.create(dict(
        foo1='foo1',
        foo2='foo2',
    ))

    c2 = copy.deepcopy(c1)
    assert c2 == c1
    c1.foo1 = "bar"
    assert c1.foo1 == 'bar'
    assert c2.foo1 == 'foo1'


def test_dict_config():
    c = OmegaConf.create(dict())
    assert isinstance(c, DictConfig)


def test_list_config_with_list():
    c = OmegaConf.create([])
    assert isinstance(c, ListConfig)


def test_list_config_with_tuple():
    c = OmegaConf.create(())
    assert isinstance(c, ListConfig)


def test_items_on_list():
    c = OmegaConf.create([1, 2])
    with raises(AttributeError):
        c.items()


def test_list_enumerate():
    src = ['a', 'b', 'c', 'd']
    c = OmegaConf.create(src)
    for i, v in enumerate(c):
        assert src[i] == v
        assert v is not None
        src[i] = None

    for v in src:
        assert v is None


def test_dict_delitem():
    c = OmegaConf.create(dict(a=10, b=11))
    assert c == dict(a=10, b=11)
    del c['a']
    assert c == dict(b=11)
    with raises(KeyError):
        del c['not_found']


def test_list_delitem():
    c = OmegaConf.create([1, 2, 3])
    assert c == [1, 2, 3]
    del c[0]
    assert c == [2, 3]
    with raises(IndexError):
        del c[100]


def test_dict_len():
    c = OmegaConf.create(dict(a=10, b=11))
    assert len(c) == 2


def test_list_len():
    c = OmegaConf.create([1, 2])
    assert len(c) == 2


class IllegalType:
    def __init__(self):
        pass


def test_dict_assign_illegal_value():
    with raises(ValueError, match=re.escape("key a")):
        c = OmegaConf.create(dict())
        c.a = IllegalType()


def test_dict_assign_illegal_value_nested():
    with raises(ValueError, match=re.escape("key a.b")):
        c = OmegaConf.create(dict(a=dict()))
        c.a.b = IllegalType()


def test_list_assign_illegal_value():
    with raises(ValueError, match=re.escape("key a[0]")):
        c = OmegaConf.create(dict(a=[None]))
        c.a[0] = IllegalType()