
#include <iostream>
#include <QApplication>
#include <QLocale>
#include <QTranslator>
#include <QLibraryInfo>

#include "util/util.h"
#include "qutil/qutil.h"
#include "appwindow.h"

int main(int argc, char *argv[])
{
    std::cout << "Qt version: " << qVersion() << std::endl;
    std::cout << "1 + 5 = " << calcSum(1,5) << std::endl;

    QApplication app(argc, argv);

    // it is not needed here, just for testing
    Q_INIT_RESOURCE(res);

    // built-into Qt translations
    QTranslator qtTranslator;
    qtTranslator.load(QStringLiteral("qt_") + QLocale::system().name(),
                        QLibraryInfo::location(QLibraryInfo::TranslationsPath));
    app.installTranslator(&qtTranslator);

    auto langDirPath = QLatin1String(":/lang");
    //auto langDirPath = QLatin1String("prog/i18n");

    // project translation
    QTranslator translator;
    bool loaded = translator.load(QLocale(), QLatin1String("i18n"),
            QLatin1String("_"), langDirPath);

    app.installTranslator(&translator);
    std::cout << "translator is loaded: " << (loaded ? "true" : "false") << std::endl;

    QTranslator translatorExtra;
    translatorExtra.load(QLocale(), QLatin1String("extra"),
            QLatin1String("_"), langDirPath);
    auto translated = translatorExtra.translate("AppWindow", "my message");
    std::cout << "translated: " << translated.toStdString() << std::endl;

    std::cout << "translated (lib): " << getTranslated().toStdString() << std::endl;

    AppWindow window;

    window.resize(500, 400);
    window.setWindowTitle("Qt5 Demo");
    window.show();

    return app.exec();
}
