#!/usr/bin/env perl

use Mojo::Loader;
use Mojo::JSON;
use Mojo::UserAgent;
use Mojo::Template;
use Mojo::Util qw/ encode decode slurp spurt /;
use FindBin '$Bin';
use Readonly;
use utf8::all;
use autodie;
use Data::Dumper;
use bytes;

#!/usr/bin/perl
use strict;

# This program attempts to translate Windows CP1252 characters in UTF-8 text

# This will work pretty well, except where a file has a CP1252 character in the range
# 0xC0-0xDF followed by one in 0x80-0xBF, or one in 0xE0-0xEF followed by two in 0x80-0xBF.
# Those (hopefully rare) cases will get translated to the wrong Unicode characters.





# Read API key and forum name from a config file using autodie
my $config_file = slurp "$Bin/conf/popular_threads_by_email.json";

my $json = Mojo::JSON->new;
my $conf = $json->decode( $config_file );

# Read the output path and filename from STDIN
my $output_file = shift @ARGV;
die 'No output file specified' unless $output_file;

# Set any constants
Readonly my $API      => $conf->{'api_url'};
Readonly my $RESOURCE => '/shares/email.json';
Readonly my $URL      => $API . $RESOURCE;

# Set arguments for the API call: api_key, forum, limit, etc.
my $args = {
    limit   => '3',
};

# Make request to The Tyee's widgets API, check response status
# If the status is okay, then decode the results from JSON
my $ua   = Mojo::UserAgent->new;
my $res = $ua->get( $URL => form => $args )->res->body;
my $data = $json->decode( $res );

# Store the array data that we're after
my $threads = $data->{'result'}{'urls'};

# Render the data in a template, TODO if we have new data
if ( $threads ) {
    my $loader   = Mojo::Loader->new;
    my $template = $loader->data( __PACKAGE__, 'list' );
    my $mt       = Mojo::Template->new;
    my $output_html = $mt->render( $template, $threads );
 
   $output_html = encode 'UTF-8', $output_html;
   

    # Write the template output to a filehandle
    spurt $output_html, $output_file;
};

__DATA__
@@ list
% my ($data) = @_;
% for my $thread ( @$data ) {
% my $title = $thread->{'title'};
% $title    =~ s/ \| The Tyee//gi;
<article class="story-item story-item--index-page story-item--minimum">
      	<h2 class="story-item__headline"><a href="<%= $thread->{'url'} %>"><%= $title %></a></h2>
      </article>
% }
