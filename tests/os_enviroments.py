import os

print('{}'.format(os.environ['HOME']))
print('{}'.format(os.environ.get('NOT_EXIST_ENV')))
# print('{}'.format(os.environ['NOT_EXIST_ENV']))

print('{}'.format(os.getenv('ENV', 'none_default_value')))
