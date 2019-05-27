import json
from enum import Enum

from django.db import models
from django.core.serializers.json import DjangoJSONEncoder


class JSONField(models.TextField):
  """
  JSONField is a generic textfield that neatly serializes/unserializes
  JSON objects seamlessly.
  Django snippet #1478

  example:
      class Page(models.Model):
          data = JSONField(blank=True, null=True)


      page = Page.objects.get(pk=5)
      page.data = {'title': 'test', 'type': 3}
      page.save()
  """

  def to_python(self, value):
    if value == "":
      return None

    try:
      if isinstance(value, str):
        return json.loads(value)
    except ValueError:
      pass
    return value

  def from_db_value(self, value, *args):
    return self.to_python(value)

  def get_db_prep_save(self, value, *args, **kwargs):
    if value == "":
      return None
    if isinstance(value, dict):
      value = json.dumps(value, cls=DjangoJSONEncoder)
    return value


class CsltEnum(Enum):
  def __int__(self):
    return self.value

  def __gt__(self, other):
    return self.value > other

  def __lt__(self, other):
    return self.value < other

  def __str__(self):
    return self.name.lower()


class Convert(models.Func):
  """
  This class is used to convert utf-8 text to other encoding text in mysql,
  generally call this function when you want to order by text with special
  encoding order, such as Chinese Pinyin order.
  """
  def __init__(self, expression, transcoding_name, **extra):
     super(Convert, self).__init__(
       expression,
       transcoding_name=transcoding_name, **extra)

  def as_mysql(self, compiler, connection):
    self.function = 'CONVERT'
    self.template = '%(function)s(%(expressions)s USING %(transcoding_name)s)'
    return super(Convert, self).as_sql(compiler, connection)
