===========================
Julius のインストール方法
===========================

このツールは Julius コマンドに依存しています.

ここでは MAC OS を対象に :code:`Julius` のコンパイル方法を
記述します.
なお, :code:`Homebrew` の導入が済んでいることを前提とします


結論
===========================

.. code-block:: bash

   $ brew install flex
   $ brew install portaudio
   $ git clone https://github.com/julius-speech/julius.git
   $ cd julius
   $ ./configure
   $ make
   $ sudo make install

確認
===========================

.. code-block:: bash

   $ julius --help
