Please note that this documentation is a work in progress. [text in square brackets] are placeholders or comments about the development of the documentation, while `<text in angle brackets>` are placeholders for the user's particular setup.

Trying out chromawallet's JSON API for exchange use
===============

Starting and stopping chromawallet from the command line
---------------

Path to the python you use (the python in the virtual environmnent if you use virtualenv, otherwise the system python)

    </path/to/python> ngccc.py startserver

Ctrl-c will stop the wallet. If that doesn't work, use the process manager on Windows to kill it. On linux you can do ps aux|grep 'ngccc.py' to find out the process number and then do:

    kill <process_number>

Running chromawallet as a service/daemon
---------------
[I have to check if this works, it usually works for python, but the GUI in chromawallet may give some trouble here. I put it in as a starting point]

You can use supervisord for this.

Supervisord is a framework for running processes and keeping them alive. Read more about it here: http://supervisord.org . Supervisord runs processes that think they are running in the foreground, such as ngccc.py but are in fact connected to supervisord. Supervisord can restart and otherwise manage ngccc.py, without the need for pid files or other such things.

On Ubuntu, you can install supervisord easily; it is one of the packages in the usual repositories. It is named "supervisor":

    sudo apt-get install supervisor

After supervisord has been installed, it has an entry in the /etc/init.d directory, and in /etc/supervisor/conf.d directory you can add a file with directions for it to run ngccc.py as a foreground process. On install supervisord is configured to start and re-start whenever the server boots.

Below is an example entry in the /etc/supervisorsuper/supervisord.conf file on a Ubuntu 14.04 LTS server for running chromawallet. In this setup example, the install directory is:

    /home/a_user_name/chromawallet_virtual_env

with the python intepreter in

                                         ./bin/python

and the chromawallet script in

                                         ./ngccc

...inside that directory.

The user it should run under is "a_user_name":

    [program:chromawallet]
    command=/home/a_user_name/chromawallet_virtual_env/bin/python ngccc.py startserver
    process_name=%(program_name)s
    numprocs=1
    directory=/home/a_user/chromawallet_virtual_env/ngccc
    stopsignal=TERM
    user=a_user_name



You can then start it the first time with 
    sudo service supervisor restart