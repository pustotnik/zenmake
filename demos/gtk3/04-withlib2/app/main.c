
#include <gtk/gtk.h>
#include "gui/gui.h"

int main(int argc, char **argv)
{

    gtk_init(&argc, &argv);

    int rv = activateGUI();
    if(rv != 0)
    {
        return rv;
    }

    gtk_main();

    return 0;
}
