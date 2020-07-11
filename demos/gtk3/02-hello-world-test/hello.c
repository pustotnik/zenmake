
// from https://developer.gnome.org/gtk3/stable/gtk-getting-started.html

#include <gtk/gtk.h>

// #if/#endif are used for testing only and actually they are not needed for this example

#if defined(WE_HAVE_GTK3) && defined(HAVE_PANGO)
static void
print_hello (GtkWidget *widget,
             gpointer   data)
{
  g_print ("Hello World, gtk3 version: %s, pango version: %s\n", GTK3_VER, LIBPANGO_VER);
}
#endif // WE_HAVE_GTK3 && HAVE_PANGO

static void
activate (GtkApplication *app,
          gpointer        user_data)
{
  GtkWidget *window;
  GtkWidget *button;
  GtkWidget *button_box;

  window = gtk_application_window_new (app);
  gtk_window_set_title (GTK_WINDOW (window), "Window");
  gtk_window_set_default_size (GTK_WINDOW (window), 200, 200);

  button_box = gtk_button_box_new (GTK_ORIENTATION_HORIZONTAL);
  gtk_container_add (GTK_CONTAINER (window), button_box);

  button = gtk_button_new_with_label ("Hello World");
  g_signal_connect (button, "clicked", G_CALLBACK (print_hello), NULL);
  g_signal_connect_swapped (button, "clicked", G_CALLBACK (gtk_widget_destroy), window);
  gtk_container_add (GTK_CONTAINER (button_box), button);

  gtk_widget_show_all (window);
}

int
main (int    argc,
      char **argv)
{
  GtkApplication *app;
  int status;

  app = gtk_application_new ("org.gtk.example", G_APPLICATION_FLAGS_NONE);
  g_signal_connect (app, "activate", G_CALLBACK (activate), NULL);
  status = g_application_run (G_APPLICATION (app), argc, argv);
  g_object_unref (app);

  return status;
}
