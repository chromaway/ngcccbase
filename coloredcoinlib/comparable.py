class ComparableMixin:
  def __ne__(self, other):
    return self != other
  def __ge__(self, other):
    return not self<other
  def __le__(self, other):
    return not other<self
