### Running chromawallet from source as a service/daemon

This step is only for those who wish to run chromawallet-server from source.


Below is an example entry in the /etc/supervisorsuper/supervisord.conf file on a Ubuntu 14.04 LTS server for running chromawallet-server. In this setup example, the install directory is:

    /home/a_user_name/chromawallet_virtual_env

with the python interpreter in

                                         ./bin

and the chromawallet script in

                                         ./ngcccbase

...inside that directory.

The file is called chromawallet.conf in this example and the user it should run under is "a_user_name":

    [program:chromawallet]
    command=/home/a_user_name/chromawallet_virtual_env/bin/python ngccc-server.py
    process_name=%(program_name)s
    numprocs=1
    directory=/home/a_user/chromawallet_virtual_env/ngcccbase
    stopsignal=TERM
    user=a_user_name



You can then re-start supervisord to load the new settings: 

    sudo service supervisor restart

At any time you can control the server with:

    sudo supervisorctl

...and issue start, stop, restart and status commands.
