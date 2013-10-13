use strict;
use warnings;

my @done;
my @todo;

my $mode = 0;

open(my $ilog, "<", "log.log") or die "Cannot open logfile: $!";

my @log = <$ilog>;

foreach (@log){
	chomp;

	if ($_ eq "end"){
		$mode = 0;
	}

	if (!$mode){
		if ($_ eq "done"){
			$mode = 1;
		} elsif ($_ eq "todo"){
			$mode = 2;
		}
	} else {
		if ($mode == 1){
			push(@done, $_);
		} elsif ($mode == 2){
			push(@todo, $_);
		}
	}
}

close($ilog);

push(@done, "");

sub getTime {
	my @time = gmtime(time);
	my $strtime = $time[2] . ":" . $time[1] . " " . $time[3] . "/" . ($time[4] + 1) . "/" . ($time[5] + 1900);
	return $strtime;
}

sub getEntry {
	my $author = $_[0];
	my $text = $_[1];
	my $strtime = getTime;
	return "$author ($strtime): $text";
}

sub help {
	print "Type \'done:\' and then type what you did \n";
	print "Example: \'done: Added function in example.py\' \n";
	print "Type \'todo\' and then type what you need to do \n";
	print "Example: \'todo: work on something better than just a logger, you lazy ass.\' \n";
	print "The dates and author will be added automatically \n";
	print "P.S. You can really go all out, regex is cool\n";
	print "Example: \'I totally DONe:   This is what I did!\'\n";
}

my $isRunning = 1;

print "Who are you: ";
my $author = <>;
chomp $author;

push(@done, getEntry($author, "Began"));

print "Everything is case insensitive\n";
print "Type help for help\n";

while ($isRunning){
	$_ = <>;

	if (/^(quit)/i){
		$isRunning = 0;
	} elsif (/^(help)/i){
		help;
	} elsif (/done:\s*(.+)/i){
		push(@done, getEntry($author, $1));
	} elsif (/todo:\s*(.+)/i){
		push(@todo, getEntry($author, $1));
	}
}

push(@done, getEntry($author, "Finished"));

open(my $olog, ">", "log.log") or die "Cannot open logfile: $!";

print $olog "done\n";
foreach (@done){
	print $olog $_ . "\n";
}
print $olog "end\n";
print $olog "todo\n";
foreach (@todo){
	print $olog $_ . "\n";
}
print $olog "end\n";

close($olog);