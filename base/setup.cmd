�  �                                                                                                                                                                                                                                                                                                                                                                                         �$Copyright (C) 1983, Digital Research�Ȏ����1���;���l���>���������O�F����lF������P��-��=������`��6���þB�����I ��������������l��9���������� �K	�< ���K	 �����
��� �K	����u����<u������������ٰ_��������m��� �������$<t"<t<t < r�����װ��������� ��;�t�AO�_�����뮰n��\��������/ �
���
�������l�6=�����6>�����6?������ �=�2����u��C������u��x�q ���6�������l�������Z����`���&�o�j ������a 
�n����< t<r<�v<�r<�v�n ��� �=	���o��.��=	� ���	 �����Ʊ��� ��$����v�<`r, ��� ��t��]���X� �S��N�*�ðp�=�����q�0� ��/�������;�����r���3��� �f���")��?	����?	 �߾/��p���T�?	�u�]�`�����j�������+�* ���]��pv}l�@	��@	,r�@	�ڰ��Ӿ����t�@	���������
��t	P��0�fX0�`�����N��������h��� �"���������{	����{	 �߾&���	�T�{	�u�]����N�n�S�T �����]����;?l�����5����;���&�J�H �
����? � ��k	�n�������&��k	�
��t� ���	 ����tP��0�uX��<0r<9wP�d� �_��ZX,0ð�Q�ܾ������`���B �|��������@ �B �d� ���@��D�B�p� ���F� ��þA��y���d�>@ t�p�i���y �@��t���;	���Y �����3����2�H���F;	�N �S  � Q��F��2�M���>Nu�S �2�R���F� �NY�Ͼd��� � �࿟	��	� �R%�?�! ��	��	�
 �T%�>� ��	��	���N%�=��t��;�7��Ë6����6��4�:�.�u�����a�W�v�N � ���H ����@ ����8 � � ���: �O���2 �k� �Y�� �� �����}��Q�)�����Y�QR����}����ZY��� � ����r/�>~U�u'� �>�|�t������D$��D�|���  � ����r�>���t#���D��r"�>���u�@�B�p������;	� ����@�B��� ��� �6��_ �����ċЭ��V���J ��� ��� ���= ^�9 ���P� �� ^��# ����u�þ��| � �z ��� �P �����
 ��m ���u�ðY�[ �� �[ �� �T �� GQW���_ ��,:��_Yt��5 ��+�K۴ ñ����t�����ù�N� � �ðr��uP�� XSQRVW�б���_^ZY[ô�ô �ò� � �                                                          �                                                                                                                                                                                                                                                                                                                                                                                                                                                                           
           Ewnqtu Evm   � O� �O� �O�CP/M-86 BIOS Customization Program for the IBM PC and XT   version 1.2 ����Ŀ
��
������ArF uC   �-P=Main Menu Second Page  SELECT BIOS CUSTOMIZATION OPTION 	
	
1 Power-On Command Line ,2 Save BIOS Parameters 
3 Memory Disk 
,4 Disk Head Step Time 5 Field Inst. Device Driver ,6 Second Page of Options 1 Verify After Disk Write ,2 Musical Error Messages 
3 Select Storage Disk 
,4 Return to Main Menu 9 Update Floppy Disk and Exit ,10Exit without Updating All modified options will take effect at the next Power-On or Reset. SELECT FUNCTION 9 Return to        This option allows a single Command Line of up to 20 characters to be executed at Power-On, or following a System Reset.   The '�' is used to show a Carriage Return (0DH).  The current Command Line is:   1 Enter a New Command Line 3 Cancel the Current Command Line 	  < none >       Terminate the new Command Line with a Carriage Return.   To put a Carriage Return within the command, type a Control-E.  To erase one character, type a Back Space (--).  ENTER A NEW COMMAND LINE       This option allows the current state of certain BIOS parameters to be saved, and reinstated at the next Power-On or System Reset.  To cancel the Save command, retype the appropriate function key.  1 Save Programmable Function Keys 3 Save Character I/O Assignments 5 Save Serial Port Configurations Saved       	      This option reserves a portion of memory to be used as a Logical Disk Drive, referred to as M:.  The user selects the starting address, and the BIOS allocates all of the contiguous memory above that address to Memory Disk.   If no memory is found at the starting address, or if the starting address is zero, then no Memory Disk will be created.  The current Starting Address is:   :0000 0123456789ABCDEF1 Enter a new Starting Address 	      Type the two most significant hexadecimal digits (0-9 or A-F) of the Starting Address segment.  The address must be within the range of 0800-9000 or C000-E000, or equal to 0000.  ENTER STARTING ADDRESS  _m  Invalid Starting Address  TYPE ANY KEY TO CONTINUE       This option controls the Verify After Write feature of the BIOS Disk Drive software.   When enabled, the Disk is verified after every write operation, with automatic retries for verification errors.  The Verify feature results in greater data security at the cost of speed.  1 Enable Verify After Write 3 Disable Verify After Write The Verify After Write feature is:   Enabled  Disabled 	      This option sets a Head Step Time of 2 to 32 mSec for the Floppy Disk Controller.  The smaller the time, the faster the Disk Head moves from track to track.   The default time is set to 8 mSec, but times of 6 mSec or 4 mSec work with some Disk Drives.  Caution is advised.  1 Decrease Head Step Time 3 Increase Head Step Time The current Disk Head Step Time is:    mSec  	      This option controls the Musical Messages which come with status line errors.   When enabled, all status line errors are accompanied by a distinctive four toned melody.  If disabled, this melody is replaced by a simple beep.  1 Enable the Musical Error Messages 3 Disable the Musical Error Messages 	Musical Error Messages are currently:   Field Installable Device Driver       This option reserves a block of memory at the top of the BIOS to be used by Field Installable Device Driver Software (FIDDS).   The use of this feature requires a separate FIDDS program capable of attaching itself to the BIOS.  For further information, refer to the application note:  "CP/M-86 FIDDS for the IBM PC".  Current FIDDS Memory Allocation is:    Kb  1 Change the FIDDS Memory Allocation 	      Type a two digit decimal number equal to the number of kilobytes you want to reserve for FIDDS.  To enter a number less than 10, type a leading zero.  To disable the FIDDS feature, type 00.  ENTER FIDDS MEMORY SIZE       This option controls which disk is used to store the information which is created by the SETUP program.  Selecting the Floppy Disk will send this information to drive A:.   Selecting the Hard Disk will send it to the Hard Disk with the lowest drive letter (usually B:).  1 Store SETUP data on Floppy Disk 3 Store SETUP data on Hard Disk The current Storage Disk is the:   Floppy Disk  Hard Disk  	                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                