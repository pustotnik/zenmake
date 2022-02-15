
#include <QtTest>
#include "qutil/qutil.h"

class TestSomeCase: public QObject
{
    Q_OBJECT

private slots:
    void testOne();
};

void TestSomeCase::testOne()
{
	QCOMPARE(calcSomething(), 42);
}

QTEST_MAIN(TestSomeCase)

#include "my_test.moc"
