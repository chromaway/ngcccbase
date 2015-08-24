from bottle import run, route, request

LINE_BUFFERED = 1

fo = open('logfile.txt', 'a', LINE_BUFFERED)


@route('/endpoint', method="POST")
def enpdpoint():
    # import pdb;pdb.set_trace()
    print request.json['message']
    fo.write(request.json['message'] + "\n")


def main():
    run(host='localhost', port=20520, debug=True)


if __name__ == '__main__':
    main()
