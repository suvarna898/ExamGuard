from faker import Faker
fake=Faker()
for i in range(10):
    print(fake.name())
    print(fake.phone_number())
    print(fake.email())