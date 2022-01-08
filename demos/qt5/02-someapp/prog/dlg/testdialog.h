
#pragma once

#include <qdialog.h>
#include "ui_testdialog.h"

class TestDialog: public QDialog
{
    Q_OBJECT

public:
    TestDialog(QWidget *parent = 0);

private:
    Ui::TestDialog _ui;
};
