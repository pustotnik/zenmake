
#include <unistd.h>
#include "gui/gui.h"

static void say_hello(GtkWidget *widget, gpointer data)
{
    g_print("Hello!\n");
}

static void say_goodbye(GtkWidget *widget, gpointer data)
{
    g_print("Goodbye!\n");
}

int activateGUI()
{
    GError* error = NULL;

    GtkBuilder* builder = gtk_builder_new();

    const gchar* uiFilePath = g_build_filename(PACKAGE_DATA_DIR, "builder.ui", NULL);
    if( access( "builder.ui", F_OK ) != -1 ) {
        uiFilePath = "builder.ui";
    }

    if(!gtk_builder_add_from_file(builder, uiFilePath, &error))
    {
        g_printerr("Error loading file: %s\n", error->message);
        g_clear_error(&error);
        return 1;
    }

    g_signal_connect(gtk_builder_get_object(builder, "window"),
        "destroy", G_CALLBACK(gtk_main_quit), NULL);

    g_signal_connect(gtk_builder_get_object(builder, "left-button"),
        "clicked", G_CALLBACK(say_hello), NULL);

    g_signal_connect(gtk_builder_get_object(builder, "right-button"),
        "clicked", G_CALLBACK(say_goodbye), NULL);

    g_signal_connect(gtk_builder_get_object(builder, "quit"),
        "clicked", G_CALLBACK(gtk_main_quit), NULL);

    return 0;
}
