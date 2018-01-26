#!/usr/bin/env perl

use Mojo::Loader;
use Mojo::JSON;
use Mojo::UserAgent;
use Mojo::Template;
use Mojo::Util qw/ encode slurp spurt /;
use FindBin '$Bin';
use Readonly;
use utf8::all;
use autodie;
use Data::Dumper;

# Read API key and forum name from a config file using autodie
my $config_file = slurp "$Bin/conf/popular_threads_by_traffic.json";

my $json = Mojo::JSON->new;
my $conf = $json->decode( $config_file );

# Read the output path and filename from STDIN
my $output_file =  shift @ARGV;
die 'No output file specified' unless $output_file;

# Set any constants
Readonly my $API      => $conf->{'api_url'};
Readonly my $RESOURCE => '/live/toppages/v3/';
Readonly my $URL      => $API . $RESOURCE;

# Set arguments for the API call: api_key, forum, limit, etc.
my $args = { 
    apikey => $conf->{'api_key'},
    host   => $conf->{'host'},
    limit   => '10',
    exclude_people => '5',
};

# Make request to Disqus API, check response status
# If the status is okay, then decode the results from JSON
my $ua   = Mojo::UserAgent->new;
my $res = $ua->get( $URL => form => $args )->res->body;
my $data = $json->decode( $res );

# Store the array data that we're after
my $threads = $data->{'pages'};


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
% my $count = 0;
<ul id="most_popular">
% for my $thread ( @$data ) {
% next if ( $thread->{'path'} eq '/' || $thread->{'path'} eq '/ReportedElsewhere/' || $thread->{'path'} =~ /MenChoose/ );
% next if ($thread->{'path'} =~ /\?utm/);
% my $title = $thread->{'title'};
% my $nopipe = substr($title, 0, index($title, '|'));
    <li><a href="<%= $thread->{'path'} %>"><%= $nopipe %></a></li>
% $count++;
% if ($count == 5) { last };
% }
</ul>
