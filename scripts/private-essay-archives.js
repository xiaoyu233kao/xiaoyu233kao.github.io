'use strict';

// Add title/date/link metadata only to archive generation, never to site.posts.
hexo.extend.filter.register('after_init', function () {
  const archiveGenerator = hexo.extend.generator.get('archive');
  if (!archiveGenerator) return;

  const moment = hexo.extend.helper.get('moment');
  const { Query } = hexo.model('Post');
  hexo.extend.generator.register('archive', function (locals) {
    const privateLinks = (locals.data.private_essays || []).map(item => ({
      title: item.title,
      date: moment(item.date).tz(this.config.timezone),
      external_url: item.external_url,
      categories: [{ name: '随笔' }]
    }));

    return archiveGenerator.call(this, {
      ...locals,
      posts: new Query(locals.posts.toArray().concat(privateLinks))
    });
  });
});
