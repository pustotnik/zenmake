#pragma once

#include <QMainWindow>

class TestDialog;

class AppWindow : public QMainWindow
{
    Q_OBJECT

signals:
	void test();

public:
    AppWindow();

private slots:
    void _showTestDialog();

private:
    TestDialog* _dlg = nullptr;
};
