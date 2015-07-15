Running chromawallet as a service/daemon
---------------

This step is optional, but íf you want to run the wallet as a service, you can use supervisord for this.

Supervisord is a framework for running processes and keeping them alive. Supervisord runs on practically all systems except Windows. You can read more about supervisord here: http://supervisord.org . Supervisord runs processes that think they are running in the foreground, such as chromawallet-server but are in fact connected to supervisord. Supervisord can start, stop and restart chromawallet-server, without the need for pid files or other such things.

On Ubuntu, you can install supervisord easily; it is one of the packages in the usual repositories. It is named "supervisor":

    sudo apt-get install supervisor

After supervisord has been installed, it has an entry in the /etc/init.d directory, and in /etc/supervisor/conf.d directory you can add a file with directions for it to run chromawallet-server . On install supervisord is configured to start immediately and then re-start every time that the server boots.

Below is an example entry in the /etc/supervisor/conf.d directory on a Ubuntu 14.04 LTS server for running chromawallet-server.

The file could be called chromawallet.conf (as long as you put conf at the end you are good to go). In this setup example, the install directory for the chromawallet-server is:

    /home/a_user_name/chromawallet

In this example the user it should run under is "a_user_name":

    [program:chromawallet]
    command=/home/a_user_name/chromawallet/chromawallet-server
    process_name=%(program_name)s
    numprocs=1
    directory=/home/a_user_name/chromawallet
    stopsignal=TERM
    user=a_user_name


You may then re-start supervisord to load the new settings:

    sudo service supervisor restart

At any time you can control the server with:

    sudo supervisorctl

...and issue start, stop, restart and status commands.
