�   �                                                                                                                                                                                                                                                                                                                                                                                          �$Copyright (C) 1983, Digital Research�Ȏ؎м���k�1����&�T%��� �� �t���u����������	�<���H�	������<
uË�Kۊ���u��!��	����*��H�	������<
uË�Kۊ���~u�����	0�����ԾC�}�>���� � ������ � ����п�� ����mR�� � �� �H Z�� @� �� ��7 �����>�+ҋ�<rB�	���*��	�6���� ������t�&m����+���þ6���N � ���� ����� ����� � � ���� �O���� �J� �Y��� ��� �������\��|����A�H�	�	B��Q�, �y ��Y��	�� � ��Q�	�k ��	Y��	��°��j ��I��Ű��] ��������S � � +��u �������	������ ������� ��CC���Q����N��Y�QR�����@����ZY�RQSP��X�.[� ��	��������	�����YZ��Ê�ۋ������	��-��	����^��	�	���	��Ё��� ���� �	��RQ�������<t�5�JGG����YZC��	����� �	���6	�1 � � �À�	���	��	�9 � �������	��6	�n�� �| �l�2 ����l �l~�" ��V�	������ ��^� ����� �w �	�����1 ���l�tVP�1 X^C��FF��	��	�10� ������r �ذr�� ���u� �j��;¸��u��þC�$�D�j�D �e�b�= ���	��� ����N� ��	���� ����� �P �����
 ��X ���u�ðY�F �� �F �� �? �� GQW���J ��,:��_Yt��  ��+�K۴ ñ����t������P�� XSQRVW�б���_^ZY[ô�ô ���W�u�� �f �>	 t� �� �>����� �� Ƌ�� ��%�	�. t&��0 �% t��' �	  � t�� �Ī�	��þX	�� �< t���Ê�< u���	�Ŀ%	� ��u؉	��t
IIt�l���l�>	sþ�	� �	�	� Q���/	� ��u ����lt�mt$
�Y�ڋ	���þ	�] ��	�W ��	�Q �	���ۋ���4 ����- �?	�s���t� � ����s�7�ƶ,��� CC��þP	�L�� ��� �N�@�V�
�9�^�5��
�/��������
�~�Ewnqtu Evm   � O� �O� �O�CP/M-86 Character I/O Assignment for the IBM PC   version 1.0 ����������Console   Aux   List  Input  Output ���)  Keyboard    Screen Serial Port 0 Serial Port 1   Printer 0   Printer 1   Printer 2 * ON *        ����Ŀ
��
������A rF  u     rSELECT LOGICAL DEVICE  ��u Assign and Exit rSELECT PHYSICAL  INPUT DEVICE  OUTPUT DEVICE u End 	
o�o���                                                  OLOAIAOCICYD2P1P0P1S0SNSDK is assigned to:   Dummy Incorrect Logical device specification Incorrect Physical device specification Input cannot be assigned to more than one device at a time Illegal type combination Device is not on-line ***   ***

The ASSIGN command may be given with or without a command tail.
Absence of a command tail invokes the Screen mode.
If a command tail is present, it must specify a Logical device
and its Type, and may specify the Physical device(s) to which
the Logical device will be assigned.

Valid Logical devices are:   CONSOLE AUXILIARY LIST
Valid device Types are:      INPUT OUTPUT
Valid Physical devices are:  KEYBOARD SCREEN SERIAL-0 SERIAL-1
                             PRINTER-0 PRINTER-1 PRINTER-2 DUMMY

Allowable abbreviations for Logical devices and Types are the
first letter of each name, and for Physical devices are the
first and last letter of each name.

This example assigns List Output to the Screen and Printer 0:

ASSIGN L O SN P0
                                                                                                                                                                                                                                                 