
#include <QApplication>

#include "appwindow.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    AppWindow window;

    window.resize(500, 300);
    window.setWindowTitle("Simple example");
    window.show();

    return app.exec();
}
