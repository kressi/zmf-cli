import requests
import fire

class ChangemanZmf:

    def audit(self):
        print('audit')

    def checkin(self):
        print('checkin')

    def build(self):
        print('build')

    def promote(self):
        print('promote')

    def package(self):
        print('package')


def main():
    fire.Fire(ChangemanZmf)

if __name__ == '__main__':
    main()
