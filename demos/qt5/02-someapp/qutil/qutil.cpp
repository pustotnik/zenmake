#include <QMap>
#include <QObject>
#include <QTranslator>
#include <QLocale>
#include "qutil.h"

// Useless class just to check compiling a class with Q_OBJECT in a '.cpp' file
class TestVal: public QObject
{
    Q_OBJECT

public:
    TestVal():_value(0) {}

    int get() const { return _value; }

public slots:
    void set(int value);

signals:
    void changed(int newValue);

private:
    int _value;
};

void TestVal::set(int value) {
    if (_value != value) {
        _value = value;
        emit changed(2 * value);
    }
}


// Calc something ...
int calcSomething()
{
    int result = 0;

    QMap<QString, int> map;
    map["one"] = 1;
    result += map.keys().size();

    TestVal a, b;
    QObject::connect(&a, &TestVal::changed, &b, &TestVal::set);
    a.set(20);
    result += b.get();

    return result + 1;
}

QString getTranslated()
{
    QTranslator translator;
    translator.load(QLocale(), QLatin1String("qutil_lang"), QLatin1String("_"),
            // TRANSLATIONS_DIR is defined via buildconf.yml
            QString::fromLocal8Bit(TRANSLATIONS_DIR));

    return translator.translate("qutil", "translated message");
}

#include "qutil.moc"
